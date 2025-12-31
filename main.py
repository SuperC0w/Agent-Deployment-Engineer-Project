import argparse
import json
import os
import sys
from openai import OpenAI

"""
An additional idea I have is to add a keyword checker to the prompt builder that would cross reference the
prompt with a database of inappropriate keywords. For example if the word fearful or scary is included in 
the prompt then that would be flagged as inappropriate. While the use of a database to check the words is
more simplistic than using another LLM to check for inappropriate keywords, I think it would be more reliable
because of this simplicity.

"""

def build_story_prompt(
    character_name: str | None = None,
    length: str | None = None,
    setting: str | None = None,
    tone: str | None = None,
    additional: str | None = None,
    debug: bool = False,
) -> str:
    """
    Assemble a structured storyteller prompt from user inputs.
    """
    guidance = [
        "Write a bedtime story for children aged 5-10.",
        "Use simple, kind language with a clear beginning, middle, and warm resolution.",
        "Keep it gentle: avoid violence, fear, or upsetting themes.",
    ]
    if length:
        guidance.append(f"Target length: {length}.")
    if character_name:
        guidance.append(f"The main character is named {character_name}.")
    if setting:
        guidance.append(f"Set the story in {setting}.")
    if tone:
        guidance.append(f"The tone should feel {tone}.")
    if additional:
        guidance.append(f"Additional instructions: {additional}.")

    guidance_text = "\n- ".join(guidance)
    if debug:
        print(
            "[debug] Storyteller prompt:\n"
            "You are a storyteller telling a story for a child about the age of 5 to 10 years old.\n"
            f"- {guidance_text}\n"
            "- Return only the story text without commentary.\n"
        )
    return (
        "You are a storyteller telling a story for a child about the age of 5 to 10 years old.\n"
        f"- {guidance_text}\n"
        "- Return only the story text without commentary."
    )


def create_story(prompt: str, api_key: str | None = None, max_tokens=3000, temperature=0.5) -> str:
    """
    Calls the model to make a story based on the prompt generated.
    """
    client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))  # prefer CLI argument, fallback to env
    if not client.api_key:
        raise ValueError("OpenAI API key not provided. Pass --openai-api-key or set OPENAI_API_KEY.")
    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message.content


def judge_story(
    story: str,
    request_context: str,
    storyteller_prompt: str,
    api_key: str | None = None,
    debug: bool = False,
) -> dict:
    """
    Use the model as a safety/quality judge for the story.
    """
    client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
    if not client.api_key:
        raise ValueError("OpenAI API key not provided. Pass --openai-api-key or set OPENAI_API_KEY.")

    system_prompt = (
        "You are a careful safety and quality judge for children's bedtime stories (ages 5-10).\n"
        "Evaluate safety (no violence, fear, or inappropriate content) and quality (clarity, warmth, coherence).\n"
        "Respond in JSON with keys:\n"
        '  safety_ok: boolean\n'
        '  safety_issues: array of strings (empty if none)\n'
        '  quality_score: integer 1-10 (10 is best)\n'
        '  justification: what is reasoning behind the scoring for the quality\n'
        '  suggestions: must include an array of up to 3 short, actionable improvement notes\n'
    )
    user_blob = (
        f"Story request/context: {request_context}\n\n"
        f"Storyteller prompt that produced the story:\n{storyteller_prompt}\n\n"
        f"Story:\n{story}"
    )
    if debug:
        print("\n[debug] Judge input payload:\n" + user_blob + "\n")
    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_blob},
        ],
        max_tokens=400,
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"raw_text": raw}
    return parsed


def refine_story(
    story: str,
    assessment: dict,
    storyteller_prompt: str,
    api_key: str | None = None,
    max_tokens=3000,
    temperature=0.5,
) -> str:
    """
    Use judge feedback to refine the story toward safety and quality.
    """
    client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
    if not client.api_key:
        raise ValueError("OpenAI API key not provided. Pass --openai-api-key or set OPENAI_API_KEY.")

    suggestions = assessment.get("suggestions") or []
    safety_issues = assessment.get("safety_issues") or []
    quality_score = assessment.get("quality_score")

    refine_instructions = [
        "Rewrite the story to address the judge feedback while keeping it for ages 5-10.",
        "Keep it gentle and positive; avoid violence, fear, or upsetting themes.",
        "Preserve the user's intent and main character/setting.",
        "Use clear, simple language with a beginning, middle, and warm resolution.",
    ]
    if safety_issues:
        refine_instructions.append(f"Fix these safety issues: {', '.join(safety_issues)}.")
    if suggestions:
        refine_instructions.append("Apply these suggestions:")
        refine_instructions.extend(f"- {s}" for s in suggestions)
    if quality_score is not None:
        refine_instructions.append(f"Target a higher quality score than {quality_score}.")

    prompt = (
        "You are revising a bedtime story using feedback from a judge.\n"
        f"{storyteller_prompt}\n\n"
        "Judge assessment and instructions:\n"
        + "\n".join(refine_instructions)
        + "\n\nOriginal story:\n"
        f"{story}\n\n"
        "Return only the revised story text."
    )

    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message.content


def main():
    parser = argparse.ArgumentParser(description="Generate a story with OpenAI.")
    parser.add_argument(
        "-k",
        "--openai-api-key",
        dest="openai_api_key",
        help="OpenAI API key (overrides OPENAI_API_KEY env var).",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Suppress intermediate output; only print the final refined story.",
    )
    args = parser.parse_args()
    debug_mode = args.debug

    character_name = input("What should the name of the character be: ")
    length_input = input("How long do you want the story to be: ")
    setting_input = input("What setting should the story take place in (e.g. 'Forest', 'City'): ")
    tone_input = input("What tone should the story have (e.g. 'adventurous and exciting, calm and cozy'): ")
    additional_input = input("Any additional instructions (optional): ")
    request_context = (
        f"Character: {character_name or 'unspecified'}; "
        f"Length: {length_input or 'unspecified'}; "
        f"Setting: {setting_input or 'unspecified'}; "
        f"Tone: {tone_input or 'unspecified'}; "
        f"Additional: {additional_input or 'unspecified'}"
    )
    story_prompt = build_story_prompt(
        character_name=character_name,
        length=length_input,
        setting=setting_input,
        tone=tone_input,
        additional=additional_input,
        debug=False if debug_mode else debug_mode,
    )
    response = create_story(story_prompt, api_key=args.openai_api_key)

    if debug_mode:
        print(response)

    assessment = judge_story(
        response,
        request_context,
        story_prompt,
        api_key=args.openai_api_key,
        debug=False if debug_mode else debug_mode,
    )
    if debug_mode:
        print("\n--- Judge Assessment ---")
        if "raw_text" in assessment:
            print(assessment["raw_text"])
        else:
            print(f"Safety OK: {assessment.get('safety_ok')}")
            if assessment.get("safety_issues"):
                print("Safety issues:")
                for issue in assessment["safety_issues"]:
                    print(f"- {issue}")
            print(f"Quality score: {assessment.get('quality_score')}")
            if assessment.get("suggestions"):
                print("Suggestions:")
                for suggestion in assessment["suggestions"]:
                    print(f"- {suggestion}")

    refined = refine_story(response, assessment, story_prompt, api_key=args.openai_api_key)
    if not debug_mode:
        print(refined)
    else:
        print("\n--- Refined Story ---")
        print(refined)


if __name__ == "__main__":
    main()
