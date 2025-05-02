import requests
import os
import base64
import re
import json
from dotenv import load_dotenv
from utils import sanitize_filename

# --- Load Environment Variables ---
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

# --- Constants ---
IMAGE_API_URL = "https://api.openai.com/v1/images/generations"
MODEL_NAME = "gpt-image-1"
IMAGE_QUALITY = "high" # Options: high, medium, low
IMAGE_SIZE = "1024x1024" # Options: 1024x1024, 1536x1024, 1024x1536, auto
OUTPUT_FORMAT = "png" # Options: png, jpeg, webp

# --- Utility Functions ---
def check_api_key():
    """Checks if the API key is available."""
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        print("Error: OPENAI_API_KEY not found or not set in .env file.")
        print("Please add your API key to the .env file.")
        return False
    return True

def generate_image(prompt_text):
    """
    Generates an image using the OpenAI Images API (gpt-image-1).

    Args:
        prompt_text (str): The text prompt for the image generation.

    Returns:
        bytes or None: The image data as bytes if successful, otherwise None.
        str or None: An error message if unsuccessful, otherwise None.
    """
    if not check_api_key():
        return None, "API key not configured."

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt_text,
        "n": 1,
        "size": IMAGE_SIZE,
        "quality": IMAGE_QUALITY,
        "output_format": OUTPUT_FORMAT,
        # "moderation": "low" # Optional: uncomment if needed
    }

    print(f"\n--- Sending request to OpenAI Images API ({MODEL_NAME}) ---")
    print(f"Prompt: {prompt_text}")
    print(f"Quality: {IMAGE_QUALITY}, Size: {IMAGE_SIZE}, Format: {OUTPUT_FORMAT}")

    try:
        response = requests.post(IMAGE_API_URL, headers=headers, json=payload)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        response_data = response.json()

        # Check response structure (gpt-image-1 specific)
        if "data" in response_data and len(response_data["data"]) > 0 and "b64_json" in response_data["data"][0]:
            b64_image_data = response_data["data"][0]["b64_json"]
            image_bytes = base64.b64decode(b64_image_data)
            print("--- Image successfully generated ---")
            if "usage" in response_data:
                print(f"Image API Usage Info: {response_data['usage']}")
            return image_bytes, None
        else:
            error_msg = "Error: Unexpected Images API response format. 'b64_json' not found."
            print(error_msg)
            print("Full Response:", json.dumps(response_data, indent=2))
            return None, error_msg

    except requests.exceptions.RequestException as e:
        error_msg = f"Error during Images API request: {e}"
        print(error_msg)
        if e.response is not None:
            print(f"Status Code: {e.response.status_code}")
            try:
                error_details = json.dumps(e.response.json(), indent=2)
                print("Error Response:", error_details)
                error_msg += f"\nDetails: {error_details}"
            except json.JSONDecodeError:
                error_details = e.response.text
                print("Error Response (non-JSON):", error_details)
                error_msg += f"\nDetails: {error_details}"
        return None, error_msg

    except Exception as e:
        error_msg = f"An unexpected error occurred during image generation: {e}"
        print(error_msg)
        return None, error_msg

def save_image(image_data, original_prompt):
    """Saves the image data to a file in the root directory."""
    if not image_data:
        print("No image data to save.")
        return

    # Create filename from sanitized prompt
    base_filename = sanitize_filename(original_prompt)
    output_filename = f"{base_filename}.{OUTPUT_FORMAT}"

    # Ensure filename is unique if it already exists
    counter = 1
    while os.path.exists(output_filename):
        output_filename = f"{base_filename}_{counter}.{OUTPUT_FORMAT}"
        counter += 1

    try:
        with open(output_filename, "wb") as f:
            f.write(image_data)
        print(f"--- Image saved successfully as {output_filename} ---")
    except IOError as e:
        print(f"Error saving image {output_filename}: {e}")

# --- Main Execution ---
if __name__ == "__main__":
    print("--- OpenAI Image Generator (gpt-image-1) ---")

    if not check_api_key():
        exit(1)

    # Get prompt from user
    try:
        user_prompt = input("Enter the image prompt: ").strip()
        if not user_prompt:
            print("Prompt cannot be empty.")
            exit(1)
    except EOFError:
        print("\nNo input received. Exiting.")
        exit(1)

    # Generate image
    image_bytes, error = generate_image(user_prompt)

    # Save image if generation was successful
    if error:
        print(f"\nImage generation failed: {error}")
    elif image_bytes:
        save_image(image_bytes, user_prompt)
    else:
        print("\nImage generation failed for an unknown reason.")

    print("\n--- Script Finished ---")
