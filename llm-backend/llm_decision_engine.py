"""
llm_decision_engine.py
-----------------------
Core AI decision engine for the solar panel system.

Architecture:
  - Uses a local transformer-based LLM via Ollama (DeepSeek-R1 or Mistral)
  - Transformer attention weighs which sensor inputs matter most per situation
  - Outputs structured JSON decisions with full reasoning chain
  - Maintains a short decision history for context (simulates memory)

Decision States:
  SUN_TRACKING   — Track the sun for maximum energy output
  CLEANING_WIND  — Tilt panel into wind to blow off dust
  CLEANING_WATER — Spray water to clean panel
  IDLE           — Park panel safely (emergency/dangerous wind)
"""

import json
import re
import time
import ollama
from typing import Dict, List, Optional


class SolarLLMDecisionEngine:
    """
    Wraps a local LLM (DeepSeek-R1 via Ollama) as an intelligent
    solar panel decision controller.
    """

    # Tunable thresholds
    DUST_THRESHOLD = 20.0           # % dust → triggers cleaning
    WIND_CLEAN_THRESHOLD = 15.0     # m/s → wind cleaning is viable
    WIND_DANGER_THRESHOLD = 40.0    # m/s → park the panel (IDLE)
    BATTERY_CRITICAL = 15.0         # % → emergency low battery
    LIGHT_MIN = 80.0                # lux → below this = nighttime

    def __init__(self, model_name: str = "deepseek-r1"):
        """
        Args:
            model_name: Ollama model tag.
                        "deepseek-r1"  — best reasoning, recommended
                        "mistral"      — faster, lighter
        """
        self.model = model_name
        self.decision_history: List[Dict] = []  # last N decisions for context
        self.MAX_HISTORY = 3

    # ──────────────────────────────────────────────────────────────────────
    # Prompt Engineering
    # ──────────────────────────────────────────────────────────────────────

    def _build_prompt(self, sensor_data: Dict) -> str:
        """
        Converts raw sensor data into a rich natural-language prompt.

        This is where the transformer's self-attention does its work:
        the model attends over the relationships between all sensor values
        simultaneously, rather than following hand-coded if/else rules.
        """

        history_block = ""
        if self.decision_history:
            history_block = "\n\nPREVIOUS DECISIONS (most recent first):\n"
            for i, h in enumerate(reversed(self.decision_history[-self.MAX_HISTORY:])):
                history_block += f"  {i+1}. Action={h['action']} | Dust={h['dust_level']}% | Wind={h['wind_speed']}m/s\n"

        prompt = f"""You are an embedded AI controller for an autonomous solar panel system.

SENSOR READINGS (current):
  Wind speed         : {sensor_data['wind_speed']} m/s
  Wind direction     : {sensor_data['wind_direction']}°
  Dust level         : {sensor_data['dust_level']}%   (0=clean, 100=fully covered)
  Battery charge     : {sensor_data['battery_pct']}%
  Light sensor       : {sensor_data['light_sensor']} lux
  Panel tilt V       : {sensor_data['servo_v']}°
  Panel tilt H       : {sensor_data['servo_h']}°
  Water used today   : {sensor_data['water_used_l']} L
  Temperature        : {sensor_data['temperature_c']}°C
  Sun intensity      : {sensor_data.get('sun_intensity_factor', 'N/A')}{history_block}

DECISION RULES (hard constraints):
  1. Wind >= {self.WIND_DANGER_THRESHOLD} m/s → ALWAYS choose IDLE (safety first)
  2. Battery < {self.BATTERY_CRITICAL}%       → ALWAYS choose IDLE (protect battery)
  3. Light < {self.LIGHT_MIN} lux             → IDLE or minimal action (nighttime)
  4. Dust >= {self.DUST_THRESHOLD}%:
       a. Wind >= {self.WIND_CLEAN_THRESHOLD} m/s → CLEANING_WIND (free, no water used)
       b. Wind <  {self.WIND_CLEAN_THRESHOLD} m/s → CLEANING_WATER (uses water reservoir)
  5. Dust < {self.DUST_THRESHOLD}% AND normal conditions → SUN_TRACKING

YOUR TASK:
Analyze ALL sensor values holistically (not just one rule at a time).
Consider edge cases, combinations, and whether previous decisions were working.
Then return ONLY a JSON object with NO markdown, NO extra text, NO code fences.

JSON SCHEMA (return exactly this structure):
{{
  "action": "SUN_TRACKING" | "CLEANING_WIND" | "CLEANING_WATER" | "IDLE",
  "action_label": "<short human-readable name>",
  "urgency": "Low" | "Medium" | "High",
  "conditions_assessment": "<2-3 sentences describing current conditions>",
  "reasoning": "<2-3 sentences explaining why this action was chosen>",
  "action_steps": ["<step 1>", "<step 2>", "<step 3>"],
  "risks_and_notes": "<any warnings, edge cases, or recommendations>",
  "confidence": <0.0 to 1.0>,
  "estimated_duration_minutes": <integer>
}}"""
        return prompt

    def _extract_json(self, raw_text: str) -> Dict:
        """
        Robustly extracts a JSON object from the model's raw output.

        DeepSeek-R1 is a reasoning model — it emits a <think>...</think>
        block before answering. This method handles:
          1. <think> blocks (strip them out)
          2. Markdown code fences (```json ... ```)
          3. Any extra text before/after the JSON object
          4. Truncated JSON (model cut off mid-response) — partial rescue
        """
        text = raw_text

        # 1. Remove DeepSeek-R1 <think> reasoning block
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

        # 2. Remove markdown code fences
        text = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()

        # 3. Try parsing directly
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 4. Find the first { and try to parse from there
        brace_start = text.find("{")
        if brace_start != -1:
            candidate = text[brace_start:]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                # 5. JSON is truncated — attempt to rescue partial fields
                # Extract whatever key:value pairs we can find
                partial = self._rescue_partial_json(candidate)
                if partial and "action" in partial:
                    return partial

        # 6. Nothing worked
        raise ValueError(f"No valid JSON found in model response:\n{text[:500]}")

    def _rescue_partial_json(self, text: str) -> Dict:
        """
        When the LLM truncates mid-JSON, extract whatever fields were
        completed and fill in safe defaults for the rest.
        """
        result = {}

        # Extract string values with regex
        str_fields = [
            "action", "action_label", "urgency",
            "conditions_assessment", "reasoning", "risks_and_notes"
        ]
        for field in str_fields:
            match = re.search(rf'"{field}"\s*:\s*"([^"]*)"', text)
            if match:
                result[field] = match.group(1)

        # Extract array field
        steps_match = re.search(r'"action_steps"\s*:\s*\[(.*?)\]', text, re.DOTALL)
        if steps_match:
            steps_raw = steps_match.group(1)
            result["action_steps"] = re.findall(r'"([^"]+)"', steps_raw)

        # Extract numeric fields
        for field in ["confidence", "estimated_duration_minutes"]:
            match = re.search(rf'"{field}"\s*:\s*([\d.]+)', text)
            if match:
                result[field] = float(match.group(1))

        # Fill safe defaults for missing required fields
        result.setdefault("action", "IDLE")
        result.setdefault("action_label", "Idle (parse error)")
        result.setdefault("urgency", "Low")
        result.setdefault("conditions_assessment", "Response was truncated — showing partial result.")
        result.setdefault("reasoning", "Model response was cut off. Try again.")
        result.setdefault("action_steps", ["Retry analysis for full results"])
        result.setdefault("risks_and_notes", "Partial response recovered. Full analysis may differ.")

        return result

    # ──────────────────────────────────────────────────────────────────────
    # Inference
    # ──────────────────────────────────────────────────────────────────────

    def decide(self, sensor_data: Dict) -> Dict:
        """
        Run the LLM on the given sensor data and return a parsed decision.

        Steps:
          1. Build prompt (sensor data → natural language)
          2. Call local LLM via Ollama (transformer inference)
          3. Parse JSON output
          4. Store in history for next call's context
        """
        prompt = self._build_prompt(sensor_data)

        start_time = time.time()

        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert embedded AI controller for solar panel hardware. "
                            "You always respond with valid JSON only. No markdown. No explanation outside JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                options={
                    "temperature": 0.2,
                    "top_p": 0.9,
                    # No num_predict limit — DeepSeek-R1 needs full token budget
                    # for its <think> block + complete JSON output
                },
            )

            inference_time = round(time.time() - start_time, 2)
            raw_text = response["message"]["content"].strip()

            decision = self._extract_json(raw_text)

            # Attach metadata
            decision["model_used"] = self.model
            decision["inference_time_seconds"] = inference_time
            decision["sensor_snapshot"] = sensor_data

            # Save to history
            self.decision_history.append({
                "action": decision.get("action"),
                "dust_level": sensor_data.get("dust_level"),
                "wind_speed": sensor_data.get("wind_speed"),
                "timestamp": sensor_data.get("timestamp"),
            })

            return {"success": True, "decision": decision}

        except (json.JSONDecodeError, ValueError) as e:
            return {
                "success": False,
                "error": f"JSON parse error: {e}",
                "raw_response": raw_text if "raw_text" in locals() else "No response",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"LLM inference error: {str(e)}",
            }

    def get_history(self) -> List[Dict]:
        return self.decision_history


# ── Quick test ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from data_generator import SolarSensorSimulator

    print("Initializing LLM Decision Engine...")
    engine = SolarLLMDecisionEngine(model_name="deepseek-r1")
    simulator = SolarSensorSimulator()

    print("Generating one sensor reading and getting LLM decision...\n")
    sensor = simulator.generate()
    print("Sensor data:")
    print(json.dumps(sensor, indent=2))
    print("\nRunning LLM inference...")

    result = engine.decide(sensor)
    if result["success"]:
        print("\nLLM Decision:")
        print(json.dumps(result["decision"], indent=2))
    else:
        print("\nError:", result["error"])
