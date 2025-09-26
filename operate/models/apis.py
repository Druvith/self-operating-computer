import base64
import io
import json
import os
import time
import traceback
from importlib import resources
from operate.exceptions import (
    ModelNotRecognizedException,
    APIError,
    ModelResponseError,
    ExecutionError,
    OCRError
)
import easyocr
import ollama
from PIL import Image
from ultralytics import YOLO
import google.generativeai as genai
from google.generativeai import protos

from operate.config import Config
from operate.exceptions import ModelNotRecognizedException
from operate.models.prompts import (
    get_system_prompt,
    get_user_first_message_prompt,
    get_user_prompt,
)
from operate.utils.label import (
    add_labels,
    get_click_position_in_percent,
    get_label_coordinates,
)
from operate.utils.ocr import get_text_coordinates, get_text_element
from operate.utils.screenshot import capture_screen_with_cursor, compress_screenshot
from operate.utils.style import ANSI_BRIGHT_MAGENTA, ANSI_GREEN, ANSI_RED, ANSI_RESET

# Load configuration
config = Config()
reader = easyocr.Reader(["en"], gpu=True)


async def get_next_action(model, messages, objective, session_id, reader):
    if config.verbose:
        print("[Self-Operating Computer][get_next_action]")
        print("[Self-Operating Computer][get_next_action] model", model)
    if model == "gpt-4":
        return call_gpt_4o(messages), None
    if model == "qwen-vl":
        operation = await call_qwen_vl_with_ocr(messages, objective, model, reader)
        return operation, None
    if model == "gpt-4-with-som":
        operation = await call_gpt_4o_labeled(messages, objective, model)
        return operation, None
    if model == "gpt-4-with-ocr":
        operation = await call_gpt_4o_with_ocr(messages, objective, model, reader)
        return operation, None
    if model == "gpt-4.1-with-ocr":
        operation = await call_gpt_4_1_with_ocr(messages, objective, model, reader)
        return operation, None
    if model == "o1-with-ocr":
        operation = await call_o1_with_ocr(messages, objective, model, reader)
        return operation, None
    if model == "agent-1":
        return "coming soon"
    if model == "gemini-pro-vision" or model == "gemini-1.5-pro":
        return call_gemini_api(messages, objective, model), None
    if model == "gemini-flash-latest" or model == "gemini-2.5-flash" or model == "gemini-2.5-pro":
        operation = await call_gemini_api_with_ocr(messages, objective, model, reader)
        return operation, None
    if model == "llava":
        operation = call_ollama_llava(messages)
        return operation, None
    if model == "claude-3":
        operation = await call_claude_3_with_ocr(messages, objective, model, reader)
        return operation, None
    raise ModelNotRecognizedException(model)


def call_gpt_4o(messages):
    if config.verbose:
        print("[call_gpt_4_v]")
    time.sleep(1)
    client = config.initialize_openai()
    try:
        screenshots_dir = "screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)

        screenshot_filename = os.path.join(screenshots_dir, "screenshot.png")
        # Call the function to capture the screen with the cursor
        capture_screen_with_cursor(screenshot_filename)

        with open(screenshot_filename, "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode("utf-8")

        if len(messages) == 1:
            user_prompt = get_user_first_message_prompt()
        else:
            user_prompt = get_user_prompt()

        if config.verbose:
            print(
                "[call_gpt_4_v] user_prompt",
                user_prompt,
            )

        vision_message = {
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"},
                },
            ],
        }
        messages.append(vision_message)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            presence_penalty=1,
            frequency_penalty=1,
        )

        content = response.choices[0].message.content

        content = clean_json(content)

        assistant_message = {"role": "assistant", "content": content}
        if config.verbose:
            print(
                "[call_gpt_4_v] content",
                content,
            )
        content = json.loads(content)

        messages.append(assistant_message)

        return content

    except Exception as e:
        print(
            f"{ANSI_GREEN}[Self-Operating Computer]{ANSI_BRIGHT_MAGENTA}[Operate] That did not work. Trying again {ANSI_RESET}",
            e,
        )
        print(
            f"{ANSI_GREEN}[Self-Operating Computer]{ANSI_RED}[Error] AI response was {ANSI_RESET}",
            content,
        )
        if config.verbose:
            traceback.print_exc()
        return call_gpt_4o(messages)


async def call_qwen_vl_with_ocr(messages, objective, model, reader):
    if config.verbose:
        print("[call_qwen_vl_with_ocr]")

    # Construct the path to the file within the package
    try:
        time.sleep(1)
        client = config.initialize_qwen()

        confirm_system_prompt(messages, objective, model)
        screenshots_dir = "screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)

        # Call the function to capture the screen with the cursor
        raw_screenshot_filename = os.path.join(screenshots_dir, "raw_screenshot.png")
        capture_screen_with_cursor(raw_screenshot_filename)

        # Compress screenshot image to make size be smaller
        screenshot_filename = os.path.join(screenshots_dir, "screenshot.jpeg")
        compress_screenshot(raw_screenshot_filename, screenshot_filename)

        with open(screenshot_filename, "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode("utf-8")

        if len(messages) == 1:
            user_prompt = get_user_first_message_prompt()
        else:
            user_prompt = get_user_prompt()

        vision_message = {
            "role": "user",
            "content": [
                {"type": "text",
                 "text": f"{user_prompt}**REMEMBER** Only output json format, do not append any other text."},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"},
                },
            ],
        }
        messages.append(vision_message)

        response = client.chat.completions.create(
            model="qwen2.5-vl-72b-instruct",
            messages=messages,
        )

        content = response.choices[0].message.content

        content = clean_json(content)

        # used later for the messages
        content_str = content

        content = json.loads(content)

        processed_content = []

        for operation in content:
            if operation.get("operation") == "click":
                text_to_click = operation.get("text")
                if config.verbose:
                    print(
                        "[call_qwen_vl_with_ocr][click] text_to_click",
                        text_to_click,
                    )
                # Initialize EasyOCR Reader
                reader = easyocr.Reader(["en"], gpu=True)

                # Read the screenshot
                result = reader.readtext(screenshot_filename)

                text_element_index = get_text_element(
                    result, text_to_click, screenshot_filename
                )
                coordinates = get_text_coordinates(
                    result, text_element_index, screenshot_filename
                )

                # add `coordinates`` to `content`
                operation["x"] = coordinates["x"]
                operation["y"] = coordinates["y"]

                if config.verbose:
                    print(
                        "[call_qwen_vl_with_ocr][click] text_element_index",
                        text_element_index,
                    )
                    print(
                        "[call_qwen_vl_with_ocr][click] coordinates",
                        coordinates,
                    )
                    print(
                        "[call_qwen_vl_with_ocr][click] final operation",
                        operation,
                    )
                processed_content.append(operation)

            else:
                processed_content.append(operation)

        # wait to append the assistant message so that if the `processed_content` step fails we don't append a message and mess up message history
        assistant_message = {"role": "assistant", "content": content_str}
        messages.append(assistant_message)

        return processed_content

    except Exception as e:
        print(
            f"{ANSI_GREEN}[Self-Operating Computer]{ANSI_BRIGHT_MAGENTA}[{model}] That did not work. Trying another method {ANSI_RESET}"
        )
        if config.verbose:
            print("[Self-Operating Computer][Operate] error", e)
            traceback.print_exc()
        return gpt_4_fallback(messages, objective, model)


async def call_gemini_api_with_ocr(messages, objective, model, reader):
    """
    Get the next action for Self-Operating Computer using Gemini API with OCR support
    """
    if config.verbose:
        print("[call_gemini_api_with_ocr]")

    for i in range(3):
        try:
            time.sleep(1)
            screenshots_dir = "screenshots"
            if not os.path.exists(screenshots_dir):
                os.makedirs(screenshots_dir)

            screenshot_filename = os.path.join(screenshots_dir, "screenshot.png")

            
            capture_screen_with_cursor(screenshot_filename)

            # Open the original screenshot
            img = Image.open(screenshot_filename)

            # Convert RGBA to RGB if necessary
            if img.mode == "RGBA":
                img = img.convert("RGB")

            # Resize the image for the model
            original_width, original_height = img.size
            aspect_ratio = original_width / original_height
            new_width = 1024  # A reasonable width for model processing
            new_height = int(new_width / aspect_ratio)
            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            prompt = get_system_prompt(model, objective)
            
            google_model = config.initialize_google(model)
            if config.verbose:
                print("[call_gemini_api_with_ocr] model", google_model)

            solve_quiz_tool = protos.Tool(
                function_declarations=[
                    protos.FunctionDeclaration(
                        name="solve_quiz",
                        description="Use this tool when you see a quiz on the screen. This tool can solve multiple-choice questions by querying a database of questions and answers.",
                        parameters=protos.Schema(
                            type=protos.Type.OBJECT,
                            properties={
                                "question": protos.Schema(type=protos.Type.STRING, description="The question to be answered"),
                                "choices": protos.Schema(type=protos.Type.ARRAY, items=protos.Schema(type=protos.Type.STRING), description="The multiple choice options"),
                            },
                            required=["question", "choices"],
                        ),
                    )
                ]
            )

            tools = [solve_quiz_tool]
            tool_config = protos.ToolConfig(
                function_calling_config=protos.FunctionCallingConfig(
                    mode=protos.FunctionCallingConfig.Mode.AUTO
                )
            )

            response = google_model.generate_content([prompt, img_resized], tools=tools, tool_config=tool_config)

            if response.candidates[0].content.parts[0].function_call.name == "solve_quiz":
                function_call = response.candidates[0].content.parts[0].function_call
                question = function_call.args["question"]
                choices = list(function_call.args["choices"])
                operation = {
                    "operation": "solve_quiz",
                    "question": question,
                    "choices": choices,
                }
                return [operation]

            content = response.text
            if config.verbose:
                print("[call_gemini_api_with_ocr] response", response)
                print("[call_gemini_api_with_ocr] content", content)

            # Clean the response if it's in markdown format
            if content.startswith("```json"):
                content = content[len("```json"):-len("```")].strip()

            # used later for the messages
            content_str = content

            content = json.loads(content)

            if "operation" not in content and "thought" in content:
                print(f"{ANSI_GREEN}[Self-Operating Computer]{ANSI_BRIGHT_MAGENTA}[{model}] Response missing 'operation'. Retrying ({i+1}/3)...{ANSI_RESET}")
                time.sleep(1)
                continue

            processed_content = []


            for operation in content:
                if operation.get("operation") == "click":
                    text_to_click = operation.get("text")
                    if config.verbose:
                        print(
                            "[call_gemini_api_with_ocr][click] text_to_click",
                            text_to_click,
                        )
                    
                    # Only use OCR if text is specified
                    if text_to_click is not None:
                        # Initialize EasyOCR Reader
                        if config.verbose:
                            print("[call_gemini_api_with_ocr][OCR] Initializing EasyOCR with English language support")
                        if config.verbose:
                            print("[call_gemini_api_with_ocr][OCR] EasyOCR reader initialized with detection and recognition models")

                        # Read the screenshot
                        if config.verbose:
                            print(f"[call_gemini_api_with_ocr][OCR] Reading text from screenshot: {screenshot_filename}")
                        result = reader.readtext(screenshot_filename)
                        if config.verbose:
                            print(f"[call_gemini_api_with_ocr][OCR] Found {len(result)} text elements")
                            for i, (bbox, text, confidence) in enumerate(result):
                                print(f"[call_gemini_api_with_ocr][OCR] Text {i}: '{text}' (confidence: {confidence:.2f})")

                        text_element_index = get_text_element(
                            result, text_to_click, screenshot_filename
                        )
                        coordinates = get_text_coordinates(
                            result, text_element_index, screenshot_filename
                        )

                        # add `coordinates`` to `content`
                        operation["x"] = coordinates["x"]
                        operation["y"] = coordinates["y"]

                        if config.verbose:
                            print(
                                "[call_gemini_api_with_ocr][click] text_element_index",
                                text_element_index,
                            )
                            print(
                                "[call_gemini_api_with_ocr][click] coordinates",
                                coordinates,
                            )
                            print(
                                "[call_gemini_api_with_ocr][click] final operation",
                                operation,
                            )
                    else:
                        if config.verbose:
                            print("[call_gemini_api_with_ocr][click] No text specified, using provided coordinates")

                    processed_content.append(operation)

                elif operation.get("operation") == "write_in":
                    label = operation.get("label")
                    content_to_write = operation.get("content") 
                    if config.verbose:
                        print(
                            f"[call_gemini_api_with_ocr][write_in] label: {label}, content: {content_to_write}"
                        )

                    #reader = easyocr.Reader(["en"], gpu=True)
                    result = reader.readtext(screenshot_filename)
                    text_element_index = get_text_element(
                        result, label, screenshot_filename
                    )
                    coordinates = get_text_coordinates(
                        result, text_element_index, screenshot_filename
                    )

                    # Assuming the input field is to the right of the label
                    operation["x"] = coordinates["x"] + 0.05 
                    operation["y"] = coordinates["y"]
                    
                    # Replace "write_in" with "click" and then add a "write" operation
                    click_operation = {"operation": "click", "x": operation["x"], "y": operation["y"]}
                    write_operation = {"operation": "write", "content": content_to_write}
                    processed_content.extend([click_operation, write_operation])

                elif operation.get("operation") == "read_text_from":
                    anchor = operation.get("anchor")
                    if config.verbose:
                        print(f"[call_gemini_api_with_ocr][read_text_from] anchor: {anchor}")

                    reader = easyocr.Reader(["en"], gpu=True)
                    result = reader.readtext(screenshot_filename)
                    
                    anchor_element_index = get_text_element(
                        result, anchor, screenshot_filename
                    )
                    anchor_coordinates = get_text_coordinates(
                        result, anchor_element_index, screenshot_filename
                    )

                    # Define a region around the anchor to read text from
                    x, y = anchor_coordinates["x"], anchor_coordinates["y"]
                    width, height = 0.2, 0.1 # Define a search area, can be adjusted
                    
                    read_text = ""
                    for i, (bbox, text, confidence) in enumerate(result):
                        text_x = (bbox[0][0] + bbox[1][0]) / 2 / Image.open(screenshot_filename).width
                        text_y = (bbox[0][1] + bbox[2][1]) / 2 / Image.open(screenshot_filename).height
                        if x < text_x < x + width and y < text_y < y + height:
                            read_text += text + " "
                    
                    # We need to re-prompt the model with the read text
                    # This is a simplified approach. A more robust solution would be to
                    # add the read text to the message history and re-run the model.
                    # For now, we'll just print it to the console.
                    print(f"[call_gemini_api_with_ocr][read_text_from] Read text: {read_text}")
                    # We don't add any operation to processed_content as this is an information gathering step

                else:
                    processed_content.append(operation)

            # wait to append the assistant message so that if the `processed_content` step fails we don't append a message and mess up message history
            assistant_message = {"role": "assistant", "content": content_str}
            messages.append(assistant_message)

            return processed_content
        except OCRError as e:
            raise ModelResponseError(f"OCR error: {e}")
        except Exception as e:
            print(
                f"{ANSI_GREEN}[Self-Operating Computer]{ANSI_BRIGHT_MAGENTA}[{model}] That did not work. Retrying ({i+1}/3)... {ANSI_RESET}"
            )
            if config.verbose:
                print(f"[call_gemini_api_with_ocr] error on attempt {i+1}: {e}")
            
            if i == 2: # If this was the last attempt
                raise ExecutionError(f"An unexpected error occurred in call_gemini_api_with_ocr after 3 attempts: {e}")
            
            time.sleep(1)

    raise ExecutionError("Failed to get a valid response from the model after 3 attempts.")

def call_gemini_api(messages, objective, model_name="gemini-2.5-flash"):
    """
    Get the next action for Self-Operating Computer using Gemini API
    """
    # Purpose: Calls the Gemini API to get the next action based on the screen content and objective.
    # - messages: The history of messages exchanged with the model.
    # - objective: The user's high-level goal.
    # - model_name: The specific Gemini model to use.
    # Comment: This function was updated to support the new Gemini API structure.
    # It now constructs a prompt with the image and text, and parses the JSON response.
    if config.verbose:
        print(
            "[Self Operating Computer][call_gemini_api]",
        )
    time.sleep(1)
    try:
        screenshots_dir = "screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)

        screenshot_filename = os.path.join(screenshots_dir, "screenshot.png")
        capture_screen_with_cursor(screenshot_filename)
        time.sleep(1)

        prompt = get_system_prompt(model_name, objective)

        model = config.initialize_google(model_name)
        if config.verbose:
            print("[call_gemini_api] model", model)

        response = model.generate_content([prompt, Image.open(screenshot_filename)])

        content = response.text
        if config.verbose:
            print("[call_gemini_api] response", response)
            print("[call_gemini_api] content", content)

        # The response might be in a markdown format, so we need to clean it
        if content.startswith("```json"):
            content = content[len("```json"):-len("```")].strip()

        content = json.loads(content)
        if config.verbose:
            print(
                "[get_next_action][call_gemini_api] content",
                content,
            )

        return content

    except Exception as e:
        print("GEMINI_API_FAILED_WITH_EXCEPTION")
        print(e)
        print(
            f"{ANSI_GREEN}[Self-Operating Computer]{ANSI_BRIGHT_MAGENTA}[Operate] That did not work. Trying another method {ANSI_RESET}"
        )
        if config.verbose:
            print("[Self-Operating Computer][Operate] error", e)
            traceback.print_exc()
        return call_gpt_4o(messages)


async def call_gpt_4o_with_ocr(messages, objective, model, reader):
    if config.verbose:
        print("[call_gpt_4o_with_ocr]")

    # Construct the path to the file within the package
    try:
        time.sleep(1)
        client = config.initialize_openai()

        confirm_system_prompt(messages, objective, model)
        screenshots_dir = "screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)

        screenshot_filename = os.path.join(screenshots_dir, "screenshot.png")
        # Call the function to capture the screen with the cursor
        capture_screen_with_cursor(screenshot_filename)

        with open(screenshot_filename, "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode("utf-8")

        if len(messages) == 1:
            user_prompt = get_user_first_message_prompt()
        else:
            user_prompt = get_user_prompt()

        vision_message = {
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"},
                },
            ],
        }
        messages.append(vision_message)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
        )

        content = response.choices[0].message.content

        content = clean_json(content)

        # used later for the messages
        content_str = content

        content = json.loads(content)

        processed_content = []

        for operation in content:
            if operation.get("operation") == "click":
                text_to_click = operation.get("text")
                if config.verbose:
                    print(
                        "[call_gpt_4o_with_ocr][click] text_to_click",
                        text_to_click,
                    )
                # Initialize EasyOCR Reader
                reader = easyocr.Reader(["en"], gpu=True)

                # Read the screenshot
                result = reader.readtext(screenshot_filename)

                text_element_index = get_text_element(
                    result, text_to_click, screenshot_filename
                )
                coordinates = get_text_coordinates(
                    result, text_element_index, screenshot_filename
                )

                # add `coordinates`` to `content`
                operation["x"] = coordinates["x"]
                operation["y"] = coordinates["y"]

                if config.verbose:
                    print(
                        "[call_gpt_4o_with_ocr][click] text_element_index",
                        text_element_index,
                    )
                    print(
                        "[call_gpt_4o_with_ocr][click] coordinates",
                        coordinates,
                    )
                    print(
                        "[call_gpt_4o_with_ocr][click] final operation",
                        operation,
                    )
                processed_content.append(operation)

            else:
                processed_content.append(operation)

        # wait to append the assistant message so that if the `processed_content` step fails we don't append a message and mess up message history
        assistant_message = {"role": "assistant", "content": content_str}
        messages.append(assistant_message)

        return processed_content

    except Exception as e:
        print(
            f"{ANSI_GREEN}[Self-Operating Computer]{ANSI_BRIGHT_MAGENTA}[{model}] That did not work. Trying another method {ANSI_RESET}"
        )
        if config.verbose:
            print("[Self-Operating Computer][Operate] error", e)
            traceback.print_exc()
        return gpt_4_fallback(messages, objective, model)


async def call_gpt_4_1_with_ocr(messages, objective, model, reader):
    if config.verbose:
        print("[call_gpt_4_1_with_ocr]")

    try:
        time.sleep(1)
        client = config.initialize_openai()

        confirm_system_prompt(messages, objective, model)
        screenshots_dir = "screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)

        screenshot_filename = os.path.join(screenshots_dir, "screenshot.png")
        capture_screen_with_cursor(screenshot_filename)

        with open(screenshot_filename, "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode("utf-8")

        if len(messages) == 1:
            user_prompt = get_user_first_message_prompt()
        else:
            user_prompt = get_user_prompt()

        vision_message = {
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"},
                },
            ],
        }
        messages.append(vision_message)

        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
        )

        content = response.choices[0].message.content

        content = clean_json(content)

        content_str = content

        content = json.loads(content)

        processed_content = []

        for operation in content:
            if operation.get("operation") == "click":
                text_to_click = operation.get("text")
                if config.verbose:
                    print(
                        "[call_gpt_4_1_with_ocr][click] text_to_click",
                        text_to_click,
                    )
                reader = easyocr.Reader(["en"], gpu=True)

                result = reader.readtext(screenshot_filename)

                text_element_index = get_text_element(
                    result, text_to_click, screenshot_filename
                )
                coordinates = get_text_coordinates(
                    result, text_element_index, screenshot_filename
                )

                operation["x"] = coordinates["x"]
                operation["y"] = coordinates["y"]

                if config.verbose:
                    print(
                        "[call_gpt_4_1_with_ocr][click] text_element_index",
                        text_element_index,
                    )
                    print(
                        "[call_gpt_4_1_with_ocr][click] coordinates",
                        coordinates,
                    )
                    print(
                        "[call_gpt_4_1_with_ocr][click] final operation",
                        operation,
                    )
                processed_content.append(operation)

            else:
                processed_content.append(operation)

        assistant_message = {"role": "assistant", "content": content_str}
        messages.append(assistant_message)

        return processed_content

    except Exception as e:
        print(
            f"{ANSI_GREEN}[Self-Operating Computer]{ANSI_BRIGHT_MAGENTA}[{model}] That did not work. Trying another method {ANSI_RESET}"
        )
        if config.verbose:
            print("[Self-Operating Computer][Operate] error", e)
            traceback.print_exc()
        return gpt_4_fallback(messages, objective, model)


async def call_o1_with_ocr(messages, objective, model, reader):
    if config.verbose:
        print("[call_o1_with_ocr]")

    # Construct the path to the file within the package
    try:
        time.sleep(1)
        client = config.initialize_openai()

        confirm_system_prompt(messages, objective, model)
        screenshots_dir = "screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)

        screenshot_filename = os.path.join(screenshots_dir, "screenshot.png")
        # Call the function to capture the screen with the cursor
        capture_screen_with_cursor(screenshot_filename)

        with open(screenshot_filename, "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode("utf-8")

        if len(messages) == 1:
            user_prompt = get_user_first_message_prompt()
        else:
            user_prompt = get_user_prompt()

        vision_message = {
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"},
                },
            ],
        }
        messages.append(vision_message)

        response = client.chat.completions.create(
            model="o1",
            messages=messages,
        )

        content = response.choices[0].message.content

        content = clean_json(content)

        # used later for the messages
        content_str = content

        content = json.loads(content)

        processed_content = []

        for operation in content:
            if operation.get("operation") == "click":
                text_to_click = operation.get("text")
                if config.verbose:
                    print(
                        "[call_o1_with_ocr][click] text_to_click",
                        text_to_click,
                    )
                # Initialize EasyOCR Reader
                reader = easyocr.Reader(["en"], gpu=True)

                # Read the screenshot
                result = reader.readtext(screenshot_filename)

                text_element_index = get_text_element(
                    result, text_to_click, screenshot_filename
                )
                coordinates = get_text_coordinates(
                    result, text_element_index, screenshot_filename
                )

                # add `coordinates`` to `content`
                operation["x"] = coordinates["x"]
                operation["y"] = coordinates["y"]

                if config.verbose:
                    print(
                        "[call_o1_with_ocr][click] text_element_index",
                        text_element_index,
                    )
                    print(
                        "[call_o1_with_ocr][click] coordinates",
                        coordinates,
                    )
                    print(
                        "[call_o1_with_ocr][click] final operation",
                        operation,
                    )
                processed_content.append(operation)

            else:
                processed_content.append(operation)

        # wait to append the assistant message so that if the `processed_content` step fails we don't append a message and mess up message history
        assistant_message = {"role": "assistant", "content": content_str}
        messages.append(assistant_message)

        return processed_content

    except Exception as e:
        print(
            f"{ANSI_GREEN}[Self-Operating Computer]{ANSI_BRIGHT_MAGENTA}[{model}] That did not work. Trying another method {ANSI_RESET}"
        )
        if config.verbose:
            print("[Self-Operating Computer][Operate] error", e)
            traceback.print_exc()
        return gpt_4_fallback(messages, objective, model)


async def call_gpt_4o_labeled(messages, objective, model):
    time.sleep(1)

    try:
        client = config.initialize_openai()

        confirm_system_prompt(messages, objective, model)
        file_path = resources.files('operate.models.weights') / 'best.pt'
        yolo_model = YOLO(file_path)  # Load your trained model
        screenshots_dir = "screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)

        screenshot_filename = os.path.join(screenshots_dir, "screenshot.png")
        # Call the function to capture the screen with the cursor
        capture_screen_with_cursor(screenshot_filename)

        with open(screenshot_filename, "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode("utf-8")

        img_base64_labeled, label_coordinates = add_labels(img_base64, yolo_model)

        if len(messages) == 1:
            user_prompt = get_user_first_message_prompt()
        else:
            user_prompt = get_user_prompt()

        if config.verbose:
            print(
                "[call_gpt_4_vision_preview_labeled] user_prompt",
                user_prompt,
            )

        vision_message = {
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img_base64_labeled}"
                    },
                },
            ],
        }
        messages.append(vision_message)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            presence_penalty=1,
            frequency_penalty=1,
        )

        content = response.choices[0].message.content

        content = clean_json(content)

        assistant_message = {"role": "assistant", "content": content}

        messages.append(assistant_message)

        content = json.loads(content)
        if config.verbose:
            print(
                "[call_gpt_4_vision_preview_labeled] content",
                content,
            )

        processed_content = []

        for operation in content:
            print(
                "[call_gpt_4_vision_preview_labeled] for operation in content",
                operation,
            )
            if operation.get("operation") == "click":
                label = operation.get("label")
                if config.verbose:
                    print(
                        "[Self Operating Computer][call_gpt_4_vision_preview_labeled] label",
                        label,
                    )

                coordinates = get_label_coordinates(label, label_coordinates)
                if config.verbose:
                    print(
                        "[Self Operating Computer][call_gpt_4_vision_preview_labeled] coordinates",
                        coordinates,
                    )
                image = Image.open(
                    io.BytesIO(base64.b64decode(img_base64)) # Load the image to get its size
                )
                image_size = image.size  # Get the size of the image (width, height)
                click_position_percent = get_click_position_in_percent(
                    coordinates, image_size
                )
                if config.verbose:
                    print(
                        "[Self Operating Computer][call_gpt_4_vision_preview_labeled] click_position_percent",
                        click_position_percent,
                    )
                if not click_position_percent:
                    print(
                        f"{ANSI_GREEN}[Self-Operating Computer]{ANSI_RED}[Error] Failed to get click position in percent. Trying another method {ANSI_RESET}"
                    )
                    return call_gpt_4o(messages)

                x_percent = f"{click_position_percent[0]:.2f}"
                y_percent = f"{click_position_percent[1]:.2f}"
                operation["x"] = x_percent
                operation["y"] = y_percent
                if config.verbose:
                    print(
                        "[Self Operating Computer][call_gpt_4_vision_preview_labeled] new click operation",
                        operation,
                    )
                processed_content.append(operation)
            else:
                if config.verbose:
                    print(
                        "[Self Operating Computer][call_gpt_4_vision_preview_labeled] .append none click operation",
                        operation,
                    )

                processed_content.append(operation)

            if config.verbose:
                print(
                    "[Self Operating Computer][call_gpt_4_vision_preview_labeled] new processed_content",
                    processed_content,
                )
            return processed_content

    except Exception as e:
        print(
            f"{ANSI_GREEN}[Self-Operating Computer]{ANSI_BRIGHT_MAGENTA}[{model}] That did not work. Trying another method {ANSI_RESET}"
        )
        if config.verbose:
            print("[Self-Operating Computer][Operate] error", e)
            traceback.print_exc()
        return call_gpt_4o(messages)

def call_ollama_llava(messages):
    if config.verbose:
        print("[call_ollama_llava]")
    time.sleep(1)
    try:
        model = config.initialize_ollama()
        screenshots_dir = "screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)

        screenshot_filename = os.path.join(screenshots_dir, "screenshot.png")
        # Call the function to capture the screen with the cursor
        capture_screen_with_cursor(screenshot_filename)

        if len(messages) == 1:
            user_prompt = get_user_first_message_prompt()
        else:
            user_prompt = get_user_prompt()

        if config.verbose:
            print(
                "[call_ollama_llava] user_prompt",
                user_prompt,
            )

        vision_message = {
            "role": "user",
            "content": user_prompt,
            "images": [screenshot_filename],
        }
        messages.append(vision_message)

        response = model.chat(
            model="llava",
            messages=messages,
        )

        # Important: Remove the image path from the message history.
        # Ollama will attempt to load each image reference and will
        # eventually timeout.
        messages[-1]["images"] = None

        content = response["message"]["content"].strip()

        content = clean_json(content)

        assistant_message = {"role": "assistant", "content": content}
        if config.verbose:
            print(
                "[call_ollama_llava] content",
                content,
            )
        content = json.loads(content)

        messages.append(assistant_message)

        return content

    except ollama.ResponseError as e:
        print(
            f"{ANSI_GREEN}[Self-Operating Computer]{ANSI_RED}[Operate] Couldn't connect to Ollama. With Ollama installed, run `ollama pull llava` then `ollama serve`{ANSI_RESET}",
            e,
        )

    except Exception as e:
        print(
            f"{ANSI_GREEN}[Self-Operating Computer]{ANSI_BRIGHT_MAGENTA}[llava] That did not work. Trying again {ANSI_RESET}",
            e,
        )
        print(
            f"{ANSI_GREEN}[Self-Operating Computer]{ANSI_RED}[Error] AI response was {ANSI_RESET}",
            content,
        )
        if config.verbose:
            traceback.print_exc()
        return call_ollama_llava(messages)


async def call_claude_3_with_ocr(messages, objective, model, reader):
    if config.verbose:
        print("[call_claude_3_with_ocr]")

    try:
        time.sleep(1)
        client = config.initialize_anthropic()

        confirm_system_prompt(messages, objective, model)
        screenshots_dir = "screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)

        screenshot_filename = os.path.join(screenshots_dir, "screenshot.png")
        capture_screen_with_cursor(screenshot_filename)

        # downsize screenshot due to 5MB size limit
        with open(screenshot_filename, "rb") as img_file:
            img = Image.open(img_file)

            # Convert RGBA to RGB
            if img.mode == "RGBA":
                img = img.convert("RGB")

            # Calculate the new dimensions while maintaining the aspect ratio
            original_width, original_height = img.size
            aspect_ratio = original_width / original_height
            new_width = 2560  # Adjust this value to achieve the desired file size
            new_height = int(new_width / aspect_ratio)
            if config.verbose:
                print("[call_claude_3_with_ocr] resizing claude")

            # Resize the image
            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Save the resized and converted image to a BytesIO object for JPEG format
            img_buffer = io.BytesIO()
            img_resized.save(
                img_buffer, format="JPEG", quality=85
            )  # Adjust the quality parameter as needed
            img_buffer.seek(0)

            # Encode the resized image as base64
            img_data = base64.b64encode(img_buffer.getvalue()).decode("utf-8")

        if len(messages) == 1:
            user_prompt = get_user_first_message_prompt()
        else:
            user_prompt = get_user_prompt()

        vision_message = {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": img_data,
                    },
                },
                {
                    "type": "text",
                    "text": user_prompt
                    + "**REMEMBER** Only output json format, do not append any other text.",
                },
            ],
        }
        messages.append(vision_message)

        # anthropic api expect system prompt as an separate argument
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=3000,
            system=messages[0]["content"],
            messages=messages[1:],
        )

        content = response.content[0].text
        content = clean_json(content)
        content_str = content
        try:
            content = json.loads(content)
        # rework for json mode output
        except json.JSONDecodeError as e:
            if config.verbose:
                print(
                    f"{ANSI_GREEN}[Self-Operating Computer]{ANSI_RED}[Error] JSONDecodeError: {e} {ANSI_RESET}"
                )
            response = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=3000,
                system=f"This json string is not valid, when using with json.loads(content) \n                it throws the following error: {e}, return correct json string. \n                **REMEMBER** Only output json format, do not append any other text.",
                messages=[{"role": "user", "content": content}],
            )
            content = response.content[0].text
            content = clean_json(content)
            content_str = content
            content = json.loads(content)

        if config.verbose:
            print(
                f"{ANSI_GREEN}[Self-Operating Computer]{ANSI_BRIGHT_MAGENTA}[{model}] content: {content} {ANSI_RESET}"
            )
        processed_content = []

        for operation in content:
            if operation.get("operation") == "click":
                text_to_click = operation.get("text")
                if config.verbose:
                    print(
                        "[call_claude_3_ocr][click] text_to_click",
                        text_to_click,
                    )
                # Initialize EasyOCR Reader
                reader = easyocr.Reader(["en"], gpu=True)

                # Read the screenshot
                result = reader.readtext(screenshot_filename)

                # limit the text to extract has a higher success rate
                text_element_index = get_text_element(
                    result, text_to_click[:3], screenshot_filename
                )
                coordinates = get_text_coordinates(
                    result, text_element_index, screenshot_filename
                )

                # add `coordinates`` to `content`
                operation["x"] = coordinates["x"]
                operation["y"] = coordinates["y"]

                if config.verbose:
                    print(
                        "[call_claude_3_ocr][click] text_element_index",
                        text_element_index,
                    )
                    print(
                        "[call_claude_3_ocr][click] coordinates",
                        coordinates,
                    )
                    print(
                        "[call_claude_3_ocr][click] final operation",
                        operation,
                    )
                processed_content.append(operation)

            else:
                processed_content.append(operation)

        assistant_message = {"role": "assistant", "content": content_str}
        messages.append(assistant_message)

        return processed_content

    except Exception as e:
        print(
            f"{ANSI_GREEN}[Self-Operating Computer]{ANSI_BRIGHT_MAGENTA}[{model}] That did not work. Trying another method {ANSI_RESET}"
        )
        if config.verbose:
            print("[Self-Operating Computer][Operate] error", e)
            traceback.print_exc()
            print("message before convertion ", messages)

        # Convert the messages to the GPT-4 format
        gpt4_messages = [messages[0]]  # Include the system message
        for message in messages[1:]:
            if message["role"] == "user":
                # Update the image type format from "source" to "url"
                updated_content = []
                for item in message["content"]:
                    if isinstance(item, dict) and "type" in item:
                        if item["type"] == "image":
                            updated_content.append(
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{item['source']['data']}"
                                    },
                                }
                            )
                        else:
                            updated_content.append(item)

                gpt4_messages.append({"role": "user", "content": updated_content})
            elif message["role"] == "assistant":
                gpt4_messages.append(
                    {"role": "assistant", "content": message["content"]}
                )

        return gpt_4_fallback(gpt4_messages, objective, model)

def get_last_assistant_message(messages):
    """
    Retrieve the last message from the assistant in the messages array.
    If the last assistant message is the first message in the array, return None.
    """
    for index in reversed(range(len(messages))):
        if messages[index]["role"] == "assistant":
            if index == 0:  # Check if the assistant message is the first in the array
                return None
            else:
                return messages[index]
    return None  # Return None if no assistant message is found

def gpt_4_fallback(messages, objective, model):
    if config.verbose:
        print("[gpt_4_fallback]")
    system_prompt = get_system_prompt("gpt-4o", objective)
    new_system_message = {"role": "system", "content": system_prompt}
    # remove and replace the first message in `messages` with `new_system_message`

    messages[0] = new_system_message

    if config.verbose:
        print("[gpt_4_fallback][updated]")
        print("[gpt_4_fallback][updated] len(messages)", len(messages))

    return call_gpt_4o(messages)

def confirm_system_prompt(messages, objective, model):
    """
    On `Exception` we default to `call_gpt_4_vision_preview` so we have this function to reassign system prompt in case of a previous failure
    """
    if config.verbose:
        print("[confirm_system_prompt] model", model)

    system_prompt = get_system_prompt(model, objective)
    new_system_message = {"role": "system", "content": system_prompt}
    # remove and replace the first message in `messages` with `new_system_message`

    messages[0] = new_system_message

    if config.verbose:
        print("[confirm_system_prompt]")
        print("[confirm_system_prompt] len(messages)", len(messages))
        for m in messages:
            if m["role"] != "user":
                print("--------------------[message]--------------------")
                print("[confirm_system_prompt][message] role", m["role"])
                print("[confirm_system_prompt][message] content", m["content"])
                print("------------------[end message]------------------")

def clean_json(content):
    if config.verbose:
        print("\n\n[clean_json] content before cleaning", content)
    if content.startswith("```json"):
        content = content[
            len("```json") :
        ].strip()  # Remove starting ```json and trim whitespace
    elif content.startswith("```"):
        content = content[
            len("```") :
        ].strip()  # Remove starting ``` and trim whitespace
    if content.endswith("```"):
        content = content[
            : -len("```")
        ].strip()  # Remove ending ``` and trim whitespace

    # Normalize line breaks and remove any unwanted characters
    content = "\n".join(line.strip() for line in content.splitlines())

    if config.verbose:
        print("\n\n[clean_json] content after cleaning", content)

    return content
