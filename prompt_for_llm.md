### Prompt for SOTA LLM

You are an expert in prompt engineering and an expert in designing training data for autonomous agents. Your task is to generate a set of high-quality, diverse, and illustrative examples for a system prompt. These examples will teach a multimodal agent how to operate a macOS computer.

**Agent Context:**

The agent, "Self-Operating Computer," perceives the screen via screenshots. It uses Optical Character Recognition (OCR) to identify UI elements by their text content. It then executes actions using a library like `pyautogui`. The agent's goal is to complete a user-defined objective by breaking it down into a sequence of operations.

**Available Operations (The Agent's "Tools"):**

The agent must output a JSON array of one or more of the following action objects. Each action has a "thought" field, which is the agent's inner monologue explaining *why* it's taking that action.

1.  **`click`**: Clicks on an element identified by its visible text. The OCR system will find the coordinates of this exact text on the screen.
    ```json
    {
      "thought": "I need to click the 'File' menu to create a new document.",
      "operation": "click",
      "text": "File"
    }
    ```

2.  **`write_in`**: Clicks on a form field's label and then types text into the associated input. This is for "click-then-type" scenarios.
    ```json
    {
      "thought": "I see a label 'Email Address', so I'll use that to input the email.",
      "operation": "write_in",
      "label": "Email Address",
      "content": "user@example.com"
    }
    ```

3.  **`write_direct`**: Types text directly without a preceding click. This is only used when a text input is *already focused* (e.g., immediately after opening Spotlight Search, or after clicking a search bar).
    ```json
    {
        "thought": "Spotlight is open and waiting for input, so I can type directly.",
        "operation": "write_direct",
        "content": "Calculator"
    }
    ```

4.  **`press`**: Simulates pressing keyboard keys or hotkeys.
    ```json
    {
      "thought": "I will save the file using the standard keyboard shortcut.",
      "operation": "press",
      "keys": ["command", "s"]
    }
    ```

5.  **`scroll`**: Scrolls the active window up or down.
    ```json
    {
      "thought": "The 'Submit' button is not visible, so I need to scroll down.",
      "operation": "scroll",
      "direction": "down"
    }
    ```

6.  **`done`**: Terminates the task when the objective is complete.
    ```json
    {
      "thought": "The file has been created and the objective is complete.",
      "operation": "done",
      "summary": "Successfully created a new folder named 'Project Alpha' on the desktop."
    }
    ```

**What Makes a Good Example:**

*   **Realism:** The task should be a common, real-world action a user would perform on a Mac.
*   **Clarity:** The "thought" for each step should be concise, logical, and clearly justify the chosen operation.
*   **Correctness:** The sequence of operations must logically achieve the task.
*   **Diversity:** The examples should cover a range of applications (e.g., web browser, file system, text editor) and operations.
*   **Showcase Nuance:** The examples must correctly distinguish between `write_in` (needs a label to click first) and `write_direct` (for already-focused fields).

**Seed Example (Follow this format precisely):**

**Objective:** Create a new folder on the desktop named 'Project Alpha'.

```json
[
  {
    "thought": "To create a new folder on the desktop, I'll first click the 'File' option in the main menu bar.",
    "operation": "click",
    "text": "File"
  },
  {
    "thought": "Now that the File menu is open, I will click on 'New Folder' to create it.",
    "operation": "click",
    "text": "New Folder"
  },
  {
    "thought": "The new folder has been created and its name is highlighted, ready for input. I can type the name directly.",
    "operation": "write_direct",
    "content": "Project Alpha"
  },
  {
    "thought": "I've typed the folder name, now I'll press enter to confirm it.",
    "operation": "press",
    "keys": ["enter"]
  },
  {
    "thought": "The folder has been created and named, so the objective is complete.",
    "operation": "done",
    "summary": "Successfully created a new folder named 'Project Alpha' on the desktop."
  }
]
```

**Please generate JSON array examples for the following scenarios:**

1.  **Scenario:** Open Chrome, go to gmail.com, and compose a new email to "friend@example.com" with the subject "Hello!" and body "Just testing."
2.  **Scenario:** Open the Calculator app using Spotlight Search and perform the calculation "125 * 4".
3.  **Scenario:** Open a web browser, navigate to Wikipedia, search for "Filament (lighting)", and scroll down to the "History" section.
4.  **Scenario:** Check if the "Slack" application is open by using the `command+tab` app switcher. If it is, switch to it. If not, open it using Spotlight.
5.  **Scenario:** Open TextEdit, write the sentence "The quick brown fox jumps over the lazy dog.", and then save the file to the desktop as "my_sentence.txt".

Provide only the valid JSON array for each scenario.
