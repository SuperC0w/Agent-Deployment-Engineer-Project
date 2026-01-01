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

## Usage
Example:
```
python main.py --openai-api-key ...
```
