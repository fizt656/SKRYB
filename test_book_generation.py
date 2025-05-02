import os
import re
import json
import time # Optional: to add delays if needed for rate limits
from openai_api import (
    generate_single_page_structure, # Using the history-based function
    generate_image_from_prompt,
    check_api_key,
    PROMPTS # Import the loaded prompts
)

# --- Hardcoded Inputs ---
BOOK_TITLE = "A Test Book, featuring Two Friends"
CHARACTERS = {
    "Baz": "a 25yo lebanese man with beard and curly hair.",
    "Maz": "a 20yo lebanese woman with flowy wavy brown hair and brown eyes."
}
STORY_OUTLINE = """Maz's family in the village of chehime in lebanon wants her to marry someone from the village, but she loves Baz. and even though her family doesn't want her to see him, he rides up on his Harley from Beirut, and Maz hops on and they go and elope, they do their 'katb lkteb'. and then they ride back to Baz's parents house where he introduces her to his family who accept her completely. the book ends with them sleeping while the sound of the city outside hugs them, as they think about the adventures they'll have together as a newly married happy couple."""
TOTAL_PAGES = 3 # Define total pages for the test run
CHOSEN_STYLE_KEY = "stage2_image_childrens" # Key from prompts.json for the desired style
CHOSEN_STYLE_DESC = "Dreamy Childrens Book" # Description matching the key

# --- Utility Function (duplicated for simplicity) ---
def sanitize_filename(name):
    """Removes or replaces characters invalid for filenames/directory names."""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'[\s.,;!]+', '_', name)
    return name[:100]

# --- Main Test Execution ---
def run_test():
    """Runs the two-stage book generation test (page-by-page text with history)."""
    print("--- Starting Test Book Generation (Page-by-Page with History) ---")
    start_time = time.time()

    # --- Check Prerequisites ---
    if not check_api_key():
        print("Test aborted: API key check failed.")
        return
    if not PROMPTS:
        print("Test aborted: Could not load prompts from prompts.json.")
        return

    # --- Setup Output Directory ---
    sanitized_title = sanitize_filename(BOOK_TITLE)
    book_dir = os.path.join("output_books", sanitized_title)
    try:
        os.makedirs(book_dir, exist_ok=True)
        print(f"Output directory: {book_dir}")
    except OSError as e:
        print(f"Test aborted: Error creating directory {book_dir}: {e}")
        return

    # --- Generate Cover Image ---
    print("\n--- Running Cover Generation ---")
    try:
        cover_template = PROMPTS['cover_image_generation']['prompt_template']
        # Include all characters on the cover
        all_char_details_string = "\n".join([f"- {name}: {desc}" for name, desc in CHARACTERS.items()])
        # Use chosen style description for cover prompt
        cover_prompt = cover_template.format(
            character_details_string=all_char_details_string,
            book_title=BOOK_TITLE.replace('_', ' '),
            style_description=CHOSEN_STYLE_DESC # Pass style description
        )
        print("Generating cover image...")
        cover_image_data, cover_error = generate_image_from_prompt(
            prompt_text=cover_prompt,
            size="1536x1024", # Changed to wide aspect ratio
            quality="high"
        )
        if cover_error:
            print(f"Error generating cover image: {cover_error}")
            # Decide if we should stop if cover fails - let's continue for now
        elif cover_image_data:
            cover_filename = os.path.join(book_dir, "cover.png")
            try:
                with open(cover_filename, "wb") as f:
                    f.write(cover_image_data)
                print(f"Cover image saved successfully as {cover_filename}")
            except IOError as e:
                print(f"Error saving cover image {cover_filename}: {e}")

    except KeyError:
        print("Error: Could not find 'cover_image_generation' or 'prompt_template' in prompts.json")
    except Exception as e:
        print(f"An unexpected error occurred during cover generation: {e}")

    # --- Loop through pages, maintaining history ---
    print("\n--- Starting Page Generation ---")
    all_pages_successful = True
    message_history = [] # Initialize empty history

    for page_num in range(1, TOTAL_PAGES + 1):
        progress_percent = int((page_num / TOTAL_PAGES) * 100) # Calculate progress
        print(f"\n===== Processing Page {page_num}/{TOTAL_PAGES} ({progress_percent}%) =====")

        # --- Stage 1: Generate Single Page Structure ---
        print(f"--- Running Stage 1: Generating Structure for Page {page_num}... ---")
        # Pass the current history and get back the updated history
        page_data, updated_history, error1 = generate_single_page_structure(
            CHARACTERS, STORY_OUTLINE, page_num, message_history, TOTAL_PAGES
        )
        message_history = updated_history # Update history for the next iteration

        if error1:
            print(f"\nError generating structure for page {page_num}: {error1}")
            all_pages_successful = False
            # Decide if we should stop or try next page even if structure fails
            # For testing, let's continue to see if subsequent pages work
            continue
        if not page_data:
            print(f"\nFailed to generate structure for page {page_num} (no error message).")
            all_pages_successful = False
            continue

        scene_desc = page_data.get("scene_description", "")
        page_text = page_data.get("page_text", "")
        print(f"--- Stage 1 Success for Page {page_num}. ---") # Added success message

        # --- Stage 2: Generate Image ---
        print(f"--- Running Stage 2: Generating Image for Page {page_num}... ---") # Added ellipsis

        # Find characters mentioned in this scene's description
        mentioned_chars = {
            name: desc for name, desc in CHARACTERS.items()
            if name.lower() in scene_desc.lower()
        }
        char_details_string = "\n".join([f"- {name}: {desc}" for name, desc in mentioned_chars.items()])
        if not char_details_string:
             char_details_string = "(No specific characters mentioned in scene description)"

        # Format the image prompt using the CHOSEN style template
        try:
            # Use the key defined at the top of the script
            img_prompt_template = PROMPTS[CHOSEN_STYLE_KEY]['prompt_template']
            image_prompt = img_prompt_template.format(
                scene_description=scene_desc,
                character_details_string=char_details_string,
                page_text=page_text
            )
        except KeyError:
            print(f"Error: Could not find '{CHOSEN_STYLE_KEY}' or 'prompt_template' in prompts.json for page {page_num}")
            all_pages_successful = False
            continue
        except Exception as e:
             print(f"Error formatting image prompt for page {page_num}: {e}")
             all_pages_successful = False
             continue

        # Generate the image
        image_data, error2 = generate_image_from_prompt(
            prompt_text=image_prompt,
            size="1536x1024",
            quality="high"
        )

        if error2:
            print(f"Error generating image for page {page_num}: {error2}")
            all_pages_successful = False
            continue

        if image_data:
            # Save the image
            output_filename = os.path.join(book_dir, f"page_{page_num:02d}.png")
            try:
                with open(output_filename, "wb") as f:
                    f.write(image_data)
                # Changed success message slightly
                print(f"--- Stage 2 Success: Page {page_num} image saved successfully as {output_filename} ---")
            except IOError as e:
                print(f"Error saving image {output_filename}: {e}")
                all_pages_successful = False
        # Optional delay
        # time.sleep(1)

    # --- Completion ---
    end_time = time.time()
    print("\n--- Test Book Generation Finished ---")
    if all_pages_successful:
        print("All pages processed successfully!")
    else:
        print("Some pages may have encountered errors during generation or saving.")
    print(f"Book pages are located in: {book_dir}")
    print(f"Total time taken: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    run_test()
