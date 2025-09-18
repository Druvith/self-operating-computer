import sys
import os
import time
import asyncio
import random
import psutil
from prompt_toolkit.shortcuts import message_dialog
from prompt_toolkit import prompt
from operate.exceptions import (
    ModelNotRecognizedException,
    APIError,
    ModelResponseError,
    ExecutionError,
    OCRError,
)
import platform
import easyocr
from operate.utils.ocr import get_text_coordinates, get_text_element

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
from operate.utils.logger import Logger
#reader = easyocr.Reader(["en"], gpu=True)

# Load configuration
config = Config()
operating_system = OperatingSystem()


def _run_operation_loop(model, objective, messages, logger, use_gpu: bool):
    """Core loop for the Self-Operating Computer, designed to be reusable."""
    # Initialize EasyOCR Reader within the loop, with specified GPU usage
    print(f"Initializing EasyOCR with use_gpu={use_gpu}...")
    reader = easyocr.Reader(["en"], gpu=use_gpu)
    print("EasyOCR initialized.")

    loop_count = 0
    session_id = None
    start_time = time.time()
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1

    while True:
        if config.verbose:
            print("[Self Operating Computer] loop_count", loop_count)

        retries = 0
        backoff_time = INITIAL_BACKOFF
        
        while retries < MAX_RETRIES:
            try:
                time.sleep(0.5)
                operations, session_id = asyncio.run(
                    get_next_action(model, messages, objective, session_id, reader)
                )

                summary = operate(operations, messages, model, start_time, logger, reader)
                if summary:
                    total_time = time.time() - start_time
                    logger.log_summary(total_time)
                    return summary  # Return the summary string on success

                break  # Break retry loop if operation is successful

            except (APIError, ModelResponseError, ExecutionError, OCRError) as e:
                retries += 1
                print(f"{ANSI_YELLOW}[Self-Operating Computer][Warning] An error occurred: {e}. Retrying ({retries}/{MAX_RETRIES})...{ANSI_RESET}")
                sleep_time = backoff_time * (2 ** retries) + random.uniform(0, 1)
                time.sleep(sleep_time)
            
            except (ModelNotRecognizedException, KeyboardInterrupt) as e:
                raise e # Re-raise fatal exceptions

            except Exception as e:
                print(f"{ANSI_RED}[Self-Operating Computer][Fatal Error] An unexpected error occurred: {e} {ANSI_RESET}")
                raise e # Re-raise other fatal errors

        if retries == MAX_RETRIES:
            raise Exception(f"Maximum retries reached after {MAX_RETRIES} attempts. Aborting.")

        loop_count += 1
        if loop_count > 50:
            raise Exception("Reached maximum loop count of 50. Aborting.")

def run_automated_test(model, objective, verbose_mode=False):
    """Automated entry point for running a test objective. Uses GPU by default for performance."""
    config.verbose = verbose_mode
    config.validation(model, voice_mode=False)
    logger = Logger()
    logger.log_task_info(objective, model)

    system_prompt = get_system_prompt(model, objective)
    messages = [{"role": "system", "content": system_prompt}]

    # This will either return a summary or raise an exception
    # It explicitly sets use_gpu=True for the automated test
    return _run_operation_loop(model, objective, messages, logger, use_gpu=True)

def main(model, terminal_prompt, voice_mode=False, verbose_mode=False):
    """Main function for interactive use of the Self-Operating Computer. Uses GPU by default."""
    logger = Logger()
    config.verbose = verbose_mode
    config.validation(model, voice_mode)

    if voice_mode:
        try:
            from whisper_mic import WhisperMic
            mic = WhisperMic()
        except ImportError:
            print(f"{ANSI_RED}Voice mode requires 'whisper_mic'. Please run 'pip install -r requirements-audio.txt'{ANSI_RESET}", flush=True)
            sys.exit(1)

    if not terminal_prompt:
        message_dialog(
            title="Self-Operating Computer",
            text="An experimental framework to enable multimodal models to operate computers",
            style=style,
        ).run()
    else:
        print("Running direct prompt...", flush=True)

    if platform.system() == "Windows":
        os.system("cls")
    else:
        print("\033c", end="", flush=True)

    if terminal_prompt:
        objective = terminal_prompt
    elif voice_mode:
        print(f"{ANSI_GREEN}[Self-Operating Computer]{ANSI_RESET} Listening for your command... (speak now)", flush=True)
        try:
            objective = mic.listen()
        except Exception as e:
            print(f"{ANSI_RED}Error in capturing voice input: {e}{ANSI_RESET}", flush=True)
            return
    else:
        print(f"[{ANSI_GREEN}Self-Operating Computer {ANSI_RESET}|{ANSI_BRIGHT_MAGENTA} {model}{ANSI_RESET}]{USER_QUESTION}", flush=True)
        print(f"{ANSI_YELLOW}[User]{ANSI_RESET}", flush=True)
        objective = prompt(style=style)

    logger.log_task_info(objective, model)
    system_prompt = get_system_prompt(model, objective)
    messages = [{"role": "system", "content": system_prompt}]

    try:
        # It explicitly sets use_gpu=True for interactive mode
        summary = _run_operation_loop(model, objective, messages, logger, use_gpu=True)
        if summary:
            print(f"{ANSI_GREEN}Objective completed successfully: {summary}{ANSI_RESET}")
    except Exception as e:
        print(f"{ANSI_RED}An error occurred: {e}{ANSI_RESET}")



def operate(operations, messages, model, start_time, logger, reader):
    if config.verbose:
        print("[Self Operating Computer][operate]", flush=True)

    for op in operations:
        if config.verbose:
            print("[Self Operating Computer][operate] operation", op, flush=True)

        operate_type = op.get("operation").lower()
        operate_thought = op.get("thought")
        operate_detail = ""
        if config.verbose:
            print("[Self Operating Computer][operate] operate_type", operate_type, flush=True)

        try:
            step_start_time = time.time()
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

                operating_system.mouse(click_detail, click=True)
            elif operate_type == "scroll":
                direction = op.get("direction")
                operate_detail = direction
                operating_system.scroll(direction)
            elif operate_type == "solve_quiz":
                question = op.get("question")
                choices = op.get("choices")
                operate_detail = f"Solving quiz for: {question}"
                
                correct_answer = solve_quiz(question, choices)
                correct_answer = correct_answer.replace("\"", "")
                
                # Find the coordinates of the correct answer on the screen
                screenshot_filename = os.path.join("screenshots", "screenshot.png")
                result = reader.readtext(screenshot_filename)
                text_element_index = get_text_element(result, correct_answer, screenshot_filename)
                coordinates = get_text_coordinates(result, text_element_index, screenshot_filename)
                
                # Click on the correct answer
                operating_system.mouse(coordinates, click=True)
                
                # Log the solve_quiz step
                step_end_time = time.time()
                logger.log_step(op, step_start_time, step_end_time)

                # Log the click step
                click_op = {"operation": "click", "x": coordinates["x"], "y": coordinates["y"]}
                logger.log_step(click_op, step_start_time, step_end_time)

                time.sleep(2)
                
                summary = f"I have solved the quiz. The correct answer for '{question}' is '{correct_answer}'. I have clicked on the answer. Moving into the next question."
                messages.append({"role": "assistant", "content": summary})
                print(f"[{ANSI_GREEN}Self-Operating Computer {ANSI_RESET}|{ANSI_BRIGHT_MAGENTA} {model}{ANSI_RESET}]", flush=True)
                print(f"{operate_thought}", flush=True)
                print(f"{ANSI_BLUE}Action: {ANSI_RESET}{summary}\n", flush=True)
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
                    f"[{ANSI_GREEN}Self-Operating Computer {ANSI_RESET}|{ANSI_BRIGHT_MAGENTA} {model}{ANSI_RESET}]", flush=True)
                print(f"{ANSI_BLUE}Objective Complete: {ANSI_RESET}{summary}\n", flush=True)
                print(f"{ANSI_BLUE}Total time taken: {ANSI_RESET}{total_time:.2f} seconds\n", flush=True)
                return True

            else:
                raise ModelResponseError(f"Unknown operation: {operate_type}")
            
            step_end_time = time.time()
            logger.log_step(op, step_start_time, step_end_time)

        except Exception as e:
            raise ExecutionError(f"Error executing operation '{operate_type}': {e}")


    print(
        f"[{ANSI_GREEN}Self-Operating Computer {ANSI_RESET}|{ANSI_BRIGHT_MAGENTA} {model}{ANSI_RESET}]", flush=True)
    print(f"{operate_thought}", flush=True)
    print(f"{ANSI_BLUE}Action: {ANSI_RESET}{operate_type} {operate_detail}\n", flush=True)

    return False
