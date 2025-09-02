import sys
import os
import time
import asyncio
from prompt_toolkit.shortcuts import message_dialog
from prompt_toolkit import prompt
from operate.exceptions import ModelNotRecognizedException
import platform

# from operate.models.prompts import USER_QUESTION, get_system_prompt
from operate.models.prompts import (
    USER_QUESTION,
    get_system_prompt,
)
from operate.config import Config
from operate.utils.style import (
    ANSI_GREEN,
    ANSI_RESET,
    ANSI_YELLOW,
    ANSI_RED,
    ANSI_BRIGHT_MAGENTA,
    ANSI_BLUE,
    style,
)
from operate.utils.operating_system import OperatingSystem
from operate.models.apis import get_next_action
from operate.tools import solve_quiz

# Load configuration
config = Config()
operating_system = OperatingSystem()


def main(model, terminal_prompt, voice_mode=False, verbose_mode=False):
    """
    Main function for the Self-Operating Computer.

    Parameters:
    - model: The model used for generating responses.
    - terminal_prompt: A string representing the prompt provided in the terminal.
    - voice_mode: A boolean indicating whether to enable voice mode.

    Returns:
    None
    """

    mic = None
    # Initialize `WhisperMic`, if `voice_mode` is True

    config.verbose = verbose_mode
    config.validation(model, voice_mode)

    if voice_mode:
        try:
            from whisper_mic import WhisperMic

            # Initialize WhisperMic if import is successful
            mic = WhisperMic()
        except ImportError:
            print(
                "Voice mode requires the 'whisper_mic' module. Please install it using 'pip install -r requirements-audio.txt'"
            )
            sys.exit(1)

    # Skip message dialog if prompt was given directly
    if not terminal_prompt:
        message_dialog(
            title="Self-Operating Computer",
            text="An experimental framework to enable multimodal models to operate computers",
            style=style,
        ).run()

    else:
        print("Running direct prompt...")

    # # Clear the console
    if platform.system() == "Windows":
        os.system("cls")
    else:
        print("\033c", end="")

    if terminal_prompt:  # Skip objective prompt if it was given as an argument
        objective = terminal_prompt
    elif voice_mode:
        print(
            f"{ANSI_GREEN}[Self-Operating Computer]{ANSI_RESET} Listening for your command... (speak now)"
        )
        try:
            objective = mic.listen()
        except Exception as e:
            print(f"{ANSI_RED}Error in capturing voice input: {e}{ANSI_RESET}")
            return  # Exit if voice input fails
    else:
        print(
            f"[{ANSI_GREEN}Self-Operating Computer {ANSI_RESET}|{ANSI_BRIGHT_MAGENTA} {model}{ANSI_RESET}]\n{USER_QUESTION}"
        )
        print(f"{ANSI_YELLOW}[User]{ANSI_RESET}")
        objective = prompt(style=style)

    system_prompt = get_system_prompt(model, objective)
    system_message = {"role": "system", "content": system_prompt}
    messages = [system_message]

    loop_count = 0

    session_id = None

    start_time = time.time()
    while True:
        if config.verbose:
            print("[Self Operating Computer] loop_count", loop_count)
        try:
            operations, session_id = asyncio.run(
                get_next_action(model, messages, objective, session_id)
            )

            stop = operate(operations, messages, model, start_time)
            if stop:
                break

            loop_count += 1
            if loop_count > 50:
                break
        except ModelNotRecognizedException as e:
            print(
                f"{ANSI_GREEN}[Self-Operating Computer]{ANSI_RED}[Error] -> {e} {ANSI_RESET}"
            )
            break
        except Exception as e:
            print(
                f"{ANSI_GREEN}[Self-Operating Computer]{ANSI_RED}[Error] -> {e} {ANSI_RESET}"
            )
            break


def operate(operations, messages, model, start_time):
    if config.verbose:
        print("[Self Operating Computer][operate]")
    for op in operations:
        if config.verbose:
            print("[Self Operating Computer][operate] operation", op)
        # wait one second
        time.sleep(1)

        operate_type = op.get("operation").lower()
        operate_thought = op.get("thought")
        operate_detail = ""
        if config.verbose:
            print("[Self Operating Computer][operate] operate_type", operate_type)

        if operate_type == "press" or operate_type == "hotkey":
            keys = op.get("keys")
            operate_detail = keys
            operating_system.press(keys)
        elif operate_type == "write":
            content = op.get("content")
            operate_detail = content
            operating_system.write(content)
        elif operate_type == "click":
            x = op.get("x")
            y = op.get("y")
            click_detail = {"x": x, "y": y}
            operate_detail = click_detail

            operating_system.mouse(click_detail)
        elif operate_type == "scroll":
            direction = op.get("direction")
            operate_detail = direction
            operating_system.scroll(direction)
        elif operate_type == "solve_quiz":
            question = op.get("question")
            choices = op.get("choices")
            operate_detail = f"Solving quiz for: {question}"
            
            correct_answer = solve_quiz(question, choices)
            
            summary = f"I have solved the quiz. The correct answer for '{question}' is '{correct_answer}'. My next action will be to click this answer."
            messages.append({"role": "assistant", "content": summary})
            print(f"[{ANSI_GREEN}Self-Operating Computer {ANSI_RESET}|{ANSI_BRIGHT_MAGENTA} {model}{ANSI_RESET}]")
            print(f"{operate_thought}")
            print(f"{ANSI_BLUE}Action: {ANSI_RESET}{summary}\n")
            continue # Proceed to the next loop to get the click action
        elif operate_type == "write_in":
            label = op.get("label")
            content = op.get("content")
            operate_detail = f'label: {label}, content: {content}'
            # The `write_in` operation is a combination of `click` and `write`
            # as handled in the `call_gemini_api_with_ocr` function.
            # We just need to handle the `click` and `write` here.
            x = op.get("x")
            y = op.get("y")
            click_detail = {"x": x, "y": y}
            operating_system.mouse(click_detail)
            operating_system.write(content)

        elif operate_type == "done":
            summary = op.get("summary")
            end_time = time.time()
            total_time = end_time - start_time

            print(
                f"[{ANSI_GREEN}Self-Operating Computer {ANSI_RESET}|{ANSI_BRIGHT_MAGENTA} {model}{ANSI_RESET}]"
            )
            print(f"{ANSI_BLUE}Objective Complete: {ANSI_RESET}{summary}\n")
            print(f"{ANSI_BLUE}Total time taken: {ANSI_RESET}{total_time:.2f} seconds\n")
            return True

        else:
            print(
                f"[{ANSI_GREEN}Self-Operating Computer]{ANSI_RED}[Error] unknown operation response :({ANSI_RESET}"
            )
            print(
                f"[{ANSI_GREEN}[Self-Operating Computer]{ANSI_RED}[Error] AI response {ANSI_RESET}{op}"
            )
            return True

        print(
            f"[{ANSI_GREEN}Self-Operating Computer {ANSI_RESET}|{ANSI_BRIGHT_MAGENTA} {model}{ANSI_RESET}]"
        )
        print(f"{operate_thought}")
        print(f"{ANSI_BLUE}Action: {ANSI_RESET}{operate_type} {operate_detail}\n")

    return False