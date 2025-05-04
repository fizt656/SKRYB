import os
import re
import json
import time # Optional: to add delays if needed for rate limits
from openai_api import (
    generate_single_page_structure, # Using the history-based function
    generate_image_from_prompt,
    edit_image_from_prompt, # Added import for image editing
    check_api_key,
    PROMPTS # Import the loaded prompts
)
from utils import sanitize_filename, get_user_input # Added get_user_input import

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
# Removed USE_EXPERIMENTAL_CONSISTENCY hardcoded variable

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

    # --- Experimental Consistency Mode Option --- # Added CLI prompt for consistency mode
    print("\nEnable Experimental Consistency Mode for Test Run? (Uses image editing for pages 1+ using previous image)") # Updated prompt
    while True:
        consistency_choice = get_user_input("Enter 'yes' or 'no':").strip().lower()
        if consistency_choice in ['yes', 'y']:
            use_experimental_consistency = True
            print("Experimental Consistency Mode enabled for test.")
            break
        elif consistency_choice in ['no', 'n']:
            use_experimental_consistency = False
            print("Experimental Consistency Mode disabled for test.")
            break
        else:
            print("Invalid choice. Please enter 'yes' or 'no'.")

    # --- Generate Cover Image ---
    print("\n--- Running Cover Generation ---")
    cover_image_data = None # Initialize cover_image_data before the try block
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

    # --- Loop through pages, maintaining history and potentially previous image ---
    print("\n--- Starting Page Generation ---")
    all_pages_successful = True
    message_history = [] # Initialize empty history
    previous_page_image_data = None # Initialize variable to store previous image data

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
            # If structure generation fails, we cannot generate an image for this page.
            # We also cannot provide a previous image for the *next* page if consistency mode is on.
            # For now, we'll just continue, which means previous_page_image_data won't be updated,
            # and the next page in consistency mode will likely fail or use an old image.
            # A more robust approach might involve skipping image generation for the next page too,
            # or attempting a standard generation if the previous image is missing.
            continue
        if not page_data:
            print(f"\nFailed to generate structure for page {page_num} (no error message).")
            all_pages_successful = False
            continue

        scene_desc = page_data.get("scene_description", "")
        page_text = page_data.get("page_text", "")
        print(f"--- Stage 1 Success for Page {page_num}. ---") # Added success message

        # --- Stage 2: Generate or Edit Image ---
        print(f"--- Running Stage 2: Generating/Editing Image for Page {page_num}... ---") # Added ellipsis

        # Find characters mentioned in this scene's description
        mentioned_chars = {
            name: desc for name, desc in CHARACTERS.items()
            if name.lower() in scene_desc.lower()
        }
        char_details_string = "\n".join([f"- {name}: {desc}" for name, desc in mentioned_chars.items()])
        if not char_details_string:
             char_details_string = "(No specific characters mentioned in scene description)"

        # --- Select and Format Image Prompt based on mode --- # Modified prompt selection logic
        image_prompt = None
        error2 = None
        img_prompt_template = None
        prompt_template_key = None # Store the key used for the prompt template

        try:
            if use_experimental_consistency:
                # Use the edit prompt template if consistency is on
                prompt_template_key = f"{CHOSEN_STYLE_KEY}_edit"
                img_prompt_template = PROMPTS[prompt_template_key]['prompt_template']
                print(f"--- Using Edit Prompt Template: {prompt_template_key} ---")
            else:
                # Use the standard generation prompt template
                prompt_template_key = CHOSEN_STYLE_KEY
                img_prompt_template = PROMPTS[prompt_template_key]['prompt_template']
                print(f"--- Using Generation Prompt Template: {prompt_template_key} ---")

            # Use the correct text variable (page_text or script_text) based on the key expected by the template
            # We'll pass both, but the template should only use one ({page_text} or {script_text})
            image_prompt = img_prompt_template.format(
                scene_description=scene_desc,
                character_details_string=char_details_string,
                page_text=page_text if CHOSEN_STYLE_KEY.endswith('childrens') else "", # Pass relevant text or empty based on original style key
                script_text=page_text if not CHOSEN_STYLE_KEY.endswith('childrens') else "" # Pass relevant text or empty based on original style key
            )
        except KeyError as e:
            # Check if the error is due to the template expecting a key that wasn't generated
            if str(e) == 'page_text' or str(e) == 'script_text': # Check for expected text keys
                 print(f"Error: Image prompt template '{prompt_template_key}' expects '{{{str(e)}}}' but it was missing in Stage 1 output for page {page_num}.")
            else:
                 print(f"Error: Could not find key '{str(e)}' in prompts.json for page {page_num}. Check prompts.json.")
            print(f"Error: Could not find '{prompt_template_key}' or 'prompt_template' in prompts.json for page {page_num}")
            all_pages_successful = False
            continue
        except Exception as e:
             print(f"Error formatting image prompt for page {page_num}: {e}")
             all_pages_successful = False
             continue

        # --- Generate or Edit Image based on mode and page number ---
        image_data = None
        error2 = None

        # Use the result of the CLI prompt (use_experimental_consistency)
        if use_experimental_consistency:
            # Use cover image for page 1, previous page image for subsequent pages
            input_image_for_edit = None
            if page_num == 1:
                input_image_for_edit = cover_image_data # Use cover image for the first page
                if input_image_for_edit:
                    print(f"--- Using Image Editing (from Cover) for Page {page_num} ---")
                else:
                    print(f"Warning: Experimental Consistency mode is on, but cover image data is missing. Falling back to standard generation for page {page_num}.")
            elif page_num > 1 and previous_page_image_data:
                input_image_for_edit = previous_page_image_data # Use previous page image
                print(f"--- Using Image Editing (from Previous Page) for Page {page_num} ---")
            else:
                print(f"Warning: Experimental Consistency mode is on, but previous page image data is missing for page {page_num}. Falling back to standard generation.")

            if input_image_for_edit:
                 image_data, error2 = edit_image_from_prompt(
                     input_image_for_edit,
                     prompt_text=image_prompt,
                     size="1536x1024", # Keep wide format for pages
                     quality="high"
                 )
            else:
                 # Fallback to standard generation if input image for edit is missing
                 image_data, error2 = generate_image_from_prompt(
                     prompt_text=image_prompt,
                     size="1536x1024", # Keep wide format for pages
                     quality="high"
                 )
        else:
            # Standard generation mode
            print(f"--- Using Standard Image Generation for Page {page_num} ---")
            image_data, error2 = generate_image_from_prompt(
                prompt_text=image_prompt,
                size="1536x1024", # Keep wide format for pages
                quality="high"
            )

        # --- Interactive Retry Loop for Image Generation/Editing Errors ---
        while error2:
            print(f"\n--- Image Generation/Editing Failed for Page {page_num} ---")
            print(f"Error: {error2}")
            print("\n--- Failed Prompt ---")
            print(image_prompt)
            print("--------------------")

            try:
                user_response = get_user_input("Enter revised prompt (or type 'SKIP' to skip image for this page): ").strip() # Use get_user_input
            except EOFError:
                print("\nNo input received, skipping image for this page.")
                user_response = "SKIP" # Treat EOF as skip

            if user_response.upper() == 'SKIP':
                print(f"Skipping image generation/editing for page {page_num}.")
                image_data = None # Ensure no image is saved
                error2 = None # Break the loop
                all_pages_successful = False # Mark as not fully successful
            else:
                print("Retrying image generation/editing with revised prompt...")
                image_prompt = user_response # Update the prompt
                # Retry using the same method (generate or edit) that failed
                if use_experimental_consistency and input_image_for_edit: # Check if we were attempting edit
                     image_data, error2 = edit_image_from_prompt(
                         input_image_for_edit, # Use the same input image as before
                         prompt_text=image_prompt,
                         size="1536x1024",
                         quality="high"
                     )
                else: # Otherwise, retry standard generation
                     image_data, error2 = generate_image_from_prompt(
                         prompt_text=image_prompt,
                         size="1536x1024",
                         quality="high"
                     )
                # Loop continues if error2 is still present after retry

        # --- Save Image (if successful or not skipped) ---
        if image_data:
            # Save the image
            output_filename = os.path.join(book_dir, f"page_{page_num:02d}.png")
            try:
                with open(output_filename, "wb") as f:
                    f.write(image_data)
                # Changed success message slightly
                print(f"--- Stage 2 Success: Page {page_num} image saved successfully as {output_filename} ---")

                # If experimental consistency is on, store this image data for the next page
                if use_experimental_consistency:
                    previous_page_image_data = image_data # Store current page's image data

            except IOError as e:
                print(f"Error saving image {output_filename}: {e}")
                all_pages_successful = False
                # If saving fails in consistency mode, the next page won't have the previous image.
                # This is handled by the fallback in the generation/editing logic.

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
