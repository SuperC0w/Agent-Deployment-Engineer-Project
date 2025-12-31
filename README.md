# Storytelling Pipeline

## Outline
```
User
  | fills in the details for character name, story tone etc.
  v
Prompt Builder
  | structures the prompt to the storyteller based on the previous details provided
  v
Storyteller 
  | draft story bsed on the prompt
  v
Judge LLM
  | provides feedback on whether the story is appropriate and feedback to improve the story
  v
Refiner
  | improves story based on feedback provided
  v
Output to User
```

## CLI knobs (current)
- Story request: asked interactively at runtime
- `--character-name` name the main character
- `--length` length guidance (e.g., `250 words`, `short`)
- `--setting` story setting (e.g., `underwater city`)
- `--mood` tone (e.g., `calm and cozy`)
- `--openai-api-key` override `OPENAI_API_KEY`

Example:
```
python main.py --character-name Luna --setting "treehouse village" --mood "warm and encouraging" --length "300 words" --openai-api-key sk-...
```
