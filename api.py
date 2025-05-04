import os
import re
import json
import time
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

# Import necessary functions from existing backend files
from openai_api import (
    generate_single_page_structure,
    generate_image_from_prompt,
    infer_characters,
    check_api_key,
    PROMPTS,
    edit_image_from_prompt
)
from utils import sanitize_filename # Assuming sanitize_filename is needed

# Define a request body model (already exists, keeping for clarity)
class BookGenerationRequest(BaseModel):
    bookTitle: str
    selectedStyle: str
    numberOfPages: int
    quickMode: bool
    characterDescriptions: str | None = None # Optional for Quick Mode
    storyOutline: str
    useExperimentalConsistency: bool

app = FastAPI()

# Add CORS middleware (already exists, keeping for clarity)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Allow requests from your Vue frontend
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (OPTIONS, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

@app.post("/generate-book")
async def generate_book(request: BookGenerationRequest):
    """
    Receives book generation parameters from the frontend and triggers the backend process.
    Adapts logic from create_book.py.
    """
    print("Received book generation request:")
    print(f"  Book Title: {request.bookTitle}")
    print(f"  Selected Style: {request.selectedStyle}")
    print(f"  Number of Pages: {request.numberOfPages}")
    print(f"  Quick Mode: {request.quickMode}")
    if not request.quickMode:
        print(f"  Character Descriptions: {request.characterDescriptions}")
    print(f"  Story Outline: {request.storyOutline}")
    print(f"  Use Experimental Consistency: {request.useExperimentalConsistency}")

    # --- Adapt Logic from create_book.py main function ---

    # Check API Key and Prompts
    if not check_api_key():
        raise HTTPException(status_code=500, detail="OpenAI API key not configured.")
    if not PROMPTS:
        raise HTTPException(status_code=500, detail="Could not load prompts from prompts.json.")

    # Get chosen style details (assuming selectedStyle from frontend matches a key in PROMPTS)
    # We need to map the frontend style key back to the style details structure in create_book.py
    # For simplicity in this integration, let's assume the frontend sends the key directly
    # and we can look up the style type from prompts.json or a similar structure.
    # A more robust solution would involve the backend providing the available styles to the frontend.

    # For now, let's try to infer style_type from the prompt key structure
    style_type = "childrens" # Default
    if "narrative" in request.selectedStyle.lower():
        style_type = "narrative"
    # This is a simplification; a better approach would be needed if style keys don't follow this pattern.

    # Infer Characters if in Quick Mode
    characters = {}
    if request.quickMode:
        print("\n--- Inferring Characters ---")
        inferred_chars, char_error = infer_characters(request.storyOutline)
        if char_error:
            raise HTTPException(status_code=500, detail=f"Error inferring characters: {char_error}")
        if not inferred_chars:
             raise HTTPException(status_code=500, detail="Could not infer characters from the concept.")
        characters = inferred_chars
        print("Inferred Characters:", characters)
    else:
        # Parse character descriptions from JSON string provided by frontend
        if request.characterDescriptions:
            try:
                characters = json.loads(request.characterDescriptions)
                if not isinstance(characters, dict):
                     raise ValueError("Character descriptions must be a JSON object.")
            except (json.JSONDecodeError, ValueError) as e:
                raise HTTPException(status_code=400, detail=f"Invalid character descriptions JSON: {e}")
        if not characters:
             raise HTTPException(status_code=400, detail="Character descriptions are required in Full Mode.")


    # Setup Output Directory
    sanitized_title = sanitize_filename(request.bookTitle)
    book_dir = os.path.join("output_books", sanitized_title)

    try:
        os.makedirs(book_dir, exist_ok=True)
        print(f"Output directory: {book_dir}")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Error creating directory {book_dir}: {e}")

    # --- Generate Cover Image (Simplified for API) ---
    # In a real API, cover generation might be a separate endpoint or handled differently.
    # For this integration, we'll include it in the main generation flow for now.
    print("\n--- Running Cover Generation ---")
    cover_image_data = None
    try:
        cover_template = PROMPTS.get('cover_image_generation', {}).get('prompt_template')
        if not cover_template:
             print("Warning: Cover image generation template not found in prompts.json. Skipping cover.")
        else:
            all_char_details_string = "\n".join([f"- {name}: {desc}" for name, desc in characters.items()])
            # Pass style description (using the frontend's selectedStyle string for now)
            cover_prompt = cover_template.format(
                character_details_string=all_char_details_string,
                book_title=request.bookTitle,
                style_description=request.selectedStyle # Use frontend style string
            )
            print("Generating cover image...")
            cover_image_data, cover_error = generate_image_from_prompt(
                prompt_text=cover_prompt,
                size="1536x1024",
                quality="high"
            )
            if cover_error:
                print(f"Error generating cover image: {cover_error}")
                # Decide if we should stop or continue without cover. Let's continue for now.
                cover_image_data = None # Ensure it's None on error
            elif cover_image_data:
                 cover_filename = os.path.join(book_dir, "cover.png")
                 try:
                     with open(cover_filename, "wb") as f:
                         f.write(cover_image_data)
                     print(f"Cover image saved successfully as {cover_filename}")
                 except IOError as e:
                     print(f"Error saving cover image {cover_filename}: {e}")


    except Exception as e:
        print(f"An unexpected error occurred during cover generation: {e}")
        # Continue without cover


    # --- Loop through pages, maintaining history and potentially previous image ---
    print("\n--- Starting Page Generation ---")
    message_history = [] # Initialize empty history
    previous_page_image_data = cover_image_data # Start with cover image data for consistency mode page 1

    for page_num in range(1, request.numberOfPages + 1):
        print(f"\n===== Processing Page {page_num}/{request.numberOfPages} =====")

        # --- Stage 1: Generate Single Page Structure ---
        print(f"--- Running Stage 1: Generating Structure for Page {page_num}... ---")
        page_data, message_history, error1 = generate_single_page_structure(
            characters, request.storyOutline, page_num, message_history, request.numberOfPages, style_type=style_type
        )

        if error1:
            print(f"\nError generating structure for page {page_num}: {error1}")
            # In an API, we might want to return an error or status update to the frontend
            # For now, we'll just log and continue to the next page
            continue
        if not page_data:
            print(f"\nFailed to generate structure for page {page_num} (no error message).")
            continue

        # Extract the correct text based on style type
        scene_desc = page_data.get("scene_description", "")
        if style_type == "narrative":
            page_content_text = page_data.get("script_text", "")
            text_key_for_image = "script_text"
        else: # childrens
            page_content_text = page_data.get("page_text", "")
            text_key_for_image = "page_text"

        if not page_content_text:
             print(f"Warning: No '{text_key_for_image}' found in Stage 1 output for page {page_num}.")


        print(f"--- Stage 1 Success for Page {page_num}. ---")

        # --- Stage 2: Generate or Edit Image ---
        print(f"--- Running Stage 2: Generating/Editing Image for Page {page_num}... ---")

        # Find characters mentioned in this scene's description
        mentioned_chars = {
            name: desc for name, desc in characters.items()
            if name.lower() in scene_desc.lower()
        }

        # Build character details string based on consistency mode and page number
        char_details_string = ""
        if request.useExperimentalConsistency and page_num > 2:
            # For later pages in consistency mode, include only character names
            char_details_string = "\n".join([f"- {name}" for name in mentioned_chars.keys()])
            if not char_details_string:
                 char_details_string = "(Characters from previous pages)" # More generic if no specific chars mentioned
        else:
            # For initial pages or without consistency mode, include full details
            char_details_string = "\n".join([f"- {name}: {desc}" for name, desc in mentioned_chars.items()])
            if not char_details_string:
                 char_details_string = "(No specific characters mentioned in scene description)"


        # Select and Format Image Prompt based on mode
        image_prompt = None
        error2 = None
        img_prompt_template = None
        prompt_template_key = None

        try:
            # Use the selectedStyle from the frontend request
            prompt_template_key = request.selectedStyle
            if request.useExperimentalConsistency and page_num > 0: # Use edit template for page 1+ if consistency is on
                 prompt_template_key = f"{request.selectedStyle}_edit"
                 # Check if the edit template exists, fallback to standard if not
                 if prompt_template_key not in PROMPTS:
                      print(f"Warning: Edit template '{prompt_template_key}' not found. Falling back to standard generation template '{request.selectedStyle}'.")
                      prompt_template_key = request.selectedStyle


            img_prompt_template = PROMPTS.get(prompt_template_key, {}).get('prompt_template')

            if not img_prompt_template:
                 raise KeyError(f"Image prompt template '{prompt_template_key}' not found in prompts.json")


            # Use the correct text variable (page_text or script_text) based on the key expected by the template
            # We'll pass both, but the template should only use one ({page_text} or {script_text})
            image_prompt = img_prompt_template.format(
                scene_description=scene_desc,
                character_details_string=char_details_string,
                page_text=page_content_text if text_key_for_image == "page_text" else "",
                script_text=page_content_text if text_key_for_image == "script_text" else ""
            )
        except KeyError as e:
            print(f"Error accessing image prompt template or formatting for page {page_num}: {e}")
            continue # Skip image generation for this page
        except Exception as e:
             print(f"Error formatting image prompt for page {page_num}: {e}")
             continue # Skip image generation for this page


        # Generate or Edit Image based on mode and page number
        image_data = None
        error2 = None

        if request.useExperimentalConsistency and page_num > 0 and previous_page_image_data:
            print(f"--- Using Image Editing for Page {page_num} ---")
            image_data, error2 = edit_image_from_prompt(
                previous_page_image_data,
                prompt_text=image_prompt,
                size="1536x1024",
                quality="high"
            )
            if error2:
                 print(f"Error during image editing for page {page_num}: {error2}")
                 print("Falling back to standard generation...")
                 # Fallback to standard generation if editing fails
                 image_data, error2 = generate_image_from_prompt(
                     prompt_text=image_prompt,
                     size="1536x1024",
                     quality="high"
                 )
                 if error2:
                      print(f"Error during fallback standard generation for page {page_num}: {error2}")
                      image_data = None # Ensure None if fallback also fails

        else:
            print(f"--- Using Standard Image Generation for Page {page_num} ---")
            image_data, error2 = generate_image_from_prompt(
                prompt_text=image_prompt,
                size="1536x1024",
                quality="high"
            )
            if error2:
                 print(f"Error during standard image generation for page {page_num}: {error2}")
                 image_data = None # Ensure None on error


        # Save Image (if successful)
        if image_data:
            output_filename = os.path.join(book_dir, f"page_{page_num:02d}.png")
            try:
                with open(output_filename, "wb") as f:
                    f.write(image_data)
                print(f"--- Stage 2 Success: Page {page_num} image saved successfully as {output_filename} ---")

                # If experimental consistency is on, store this image data for the next page
                if request.useExperimentalConsistency:
                    previous_page_image_data = image_data

            except IOError as e:
                print(f"Error saving image {output_filename}: {e}")
                # Continue even if saving fails

        # Optional delay
        # time.sleep(1)

    print("\n--- Book Generation Process Completed ---")
    return {"message": "Book generation started. Check output_books directory."}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
