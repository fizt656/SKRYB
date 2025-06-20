import os
import time
import replicate
from dotenv import load_dotenv

load_dotenv()

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

def check_replicate_api_key():
    """Check if the Replicate API key is configured."""
    return bool(REPLICATE_API_TOKEN)

def generate_image_with_replicate(prompt_text: str, input_image: str | None = None, safety_tolerance: int | None = None):
    """
    Generates an image using the Replicate API with an optional input image.
    This function now uses the full prediction lifecycle for more robust handling.
    """
    if not check_replicate_api_key():
        return None, "Replicate API key not configured."

    try:
        input_params = {
            "prompt": prompt_text,
            "output_format": "jpg",
        }
        if input_image:
            input_params["input_image"] = input_image
            input_params["aspect_ratio"] = "match_input_image"
            input_params["safety_tolerance"] = safety_tolerance if safety_tolerance is not None else 2
        else:
            input_params["aspect_ratio"] = "1:1"
            input_params["safety_tolerance"] = safety_tolerance if safety_tolerance is not None else 6

        # Step 1: Create the prediction
        prediction = replicate.predictions.create(
            model="black-forest-labs/flux-kontext-max",
            input=input_params
        )

        # Step 2: Poll for the prediction result
        while prediction.status not in ["succeeded", "failed", "canceled"]:
            time.sleep(2) # Wait for 2 seconds before checking again
            prediction = replicate.predictions.get(prediction.id)

        # Step 3: Handle the result
        if prediction.status == "succeeded":
            image_url = prediction.output
            if isinstance(image_url, list):
                image_url = image_url[0]

            if image_url and isinstance(image_url, str):
                import requests
                response = requests.get(image_url)
                response.raise_for_status()
                return response.content, None
            else:
                return None, "Failed to get a valid image URL from the successful prediction."
        else:
            return None, f"Prediction failed with status: {prediction.status}. Error: {prediction.error}"

    except Exception as e:
        return None, f"An error occurred with the Replicate API: {e}"
