import os
import re
import json
import time
import sys # For exiting
from openai_api import (
    generate_single_page_structure, # Use the history-based function
    generate_image_from_prompt,
    infer_characters, # Import the new function
    check_api_key,
    PROMPTS, # Import the loaded prompts
    edit_image_from_prompt # Import the edit function
)
from utils import sanitize_filename, get_user_input

def main():
    """Main function to run the two-stage book creation CLI."""
    print("Welcome to SKRYB - The AI Book Generator!")
    start_time = time.time()

    # --- Mode Selection ---
    print("\nChoose Generation Mode:")
    print("1: Full Mode (Define characters and outline)")
    print("2: Quick Mode (Provide concept, characters inferred)")
    while True:
        mode_choice = input("Enter mode number (1 or 2): ").strip()
        if mode_choice == '1':
            quick_mode = False
            print("Full Mode selected.")
            break
        elif mode_choice == '2':
            quick_mode = True
            print("Quick Mode selected.")
            break
        else:
            print("Invalid choice. Please enter 1 or 2.")

    # --- Define Styles ---
    styles = {
        "1": {"key": "stage2_image_childrens", "desc": "Dreamy Childrens Book", "type": "childrens"},
        "2": {"key": "stage2_image_dark_anime", "desc": "Dark Anime SciFi", "type": "narrative"},
        "3": {"key": "stage2_image_dreamy_anime", "desc": "Dreamy Anime", "type": "narrative"},
        "4": {"key": "stage2_image_70s_cartoon", "desc": "70s Funky Cartoon", "type": "narrative"},
        "5": {"key": "stage2_image_mgs_comic", "desc": "MGS Comic Book Style", "type": "narrative"},
        "6": {"key": "stage2_image_cinematic_film_still", "desc": "Realistic Cinematic Film Still", "type": "narrative"} # Added cinematic style
    }

    # --- Check Prerequisites ---
    if not check_api_key():
        return
    if not PROMPTS:
        print("Error: Could not load prompts from prompts.json. Exiting.")
        return

    # --- Get Common User Choices ---
    book_title = get_user_input("\nEnter a title for your book:")

    print("\nChoose an illustration style:")
    for key, value in styles.items():
        print(f"{key}: {value['desc']}")

    while True:
        style_choice = input("Enter the number for your chosen style: ").strip()
        if style_choice in styles:
            chosen_style = styles[style_choice]
            print(f"Style selected: {chosen_style['desc']}")
            break
        else:
            print("Invalid choice. Please enter a number from the list.")

    while True:
        try:
            total_pages_str = get_user_input("\nEnter the total number of pages for the book (e.g., 10):")
            total_pages = int(total_pages_str)
            if total_pages > 0:
                break
            else:
                print("Number of pages must be positive.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    # --- Experimental Consistency Mode Option ---
    print("\nEnable Experimental Consistency Mode? (Uses image editing for pages 1+ using previous image)") # Updated prompt
    while True:
        consistency_choice = input("Enter 'yes' or 'no': ").strip().lower()
        if consistency_choice in ['yes', 'y']:
            use_experimental_consistency = True
            print("Experimental Consistency Mode enabled.")
            break
        elif consistency_choice in ['no', 'n']:
            use_experimental_consistency = False
            print("Experimental Consistency Mode disabled.")
            break
        else:
            print("Invalid choice. Please enter 'yes' or 'no'.")


    # --- Get Mode-Specific Inputs ---
    if quick_mode:
        story_outline = get_user_input(
            "\nEnter a basic concept or theme for the story:",
            multi_line=True
        )
        print("\n--- Inferring Characters ---")
        characters, char_error = infer_characters(story_outline)
        if char_error:
            print(f"Error inferring characters: {char_error}")
            print("Please try again or use Full Mode.")
            sys.exit(1) # Exit if character inference fails
        if not characters:
             print("Could not infer characters from the concept. Please try a more descriptive concept or use Full Mode.")
             sys.exit(1)
        print("Inferred Characters:")
        for name, desc in characters.items():
            print(f"- {name}: {desc}")

    else: # Full Mode
        characters = {}
        print("\n--- Character Descriptions ---")
        while True:
            char_name = input("Enter character name (or leave blank to finish): ").strip()
            if not char_name:
                if not characters:
                    print("You must define at least one character.")
                    continue
                else:
                    break
            char_desc = get_user_input(f"Describe '{char_name}' (e.g., appearance, clothing):")
            characters[char_name] = char_desc
            print(f"Character '{char_name}' added.")

        story_outline = get_user_input(
            f"\nEnter a general outline or theme for the {total_pages}-page story:", # Use dynamic page count
            multi_line=True
        )


    # --- Setup Output Directory ---
    sanitized_title = sanitize_filename(book_title)
    book_dir = os.path.join("output_books", sanitized_title)

    try:
        os.makedirs(book_dir, exist_ok=True)
        print(f"Output directory: {book_dir}")
    except OSError as e:
        print(f"Error creating directory {book_dir}: {e}")
        return

    # --- Generate Cover Image ---
    print("\n--- Running Cover Generation ---")
    cover_image_data = None # Initialize cover_image_data before the try block
    try:
        cover_template = PROMPTS['cover_image_generation']['prompt_template']
        all_char_details_string = "\n".join([f"- {name}: {desc}" for name, desc in characters.items()])
        # Pass style description to cover prompt
        cover_prompt = cover_template.format(
            character_details_string=all_char_details_string,
            book_title=book_title,
            style_description=chosen_style['desc'] # Pass style description
        )
        print("Generating cover image...")
        cover_image_data, cover_error = generate_image_from_prompt(
            prompt_text=cover_prompt,
            size="1536x1024", # Changed to wide aspect ratio
            quality="high"
        )

        # --- Interactive Retry Loop for Cover Image Errors ---
        while cover_error:
            print(f"\n--- Cover Image Generation Failed ---")
            print(f"Error: {cover_error}")
            print("\n--- Failed Prompt ---")
            print(cover_prompt)
            print("--------------------------")

            try:
                user_response = get_user_input("Enter revised prompt for cover (or type 'SKIP' to skip cover image): ").strip() # Use get_user_input
            except EOFError:
                print("\nNo input received, skipping cover image.")
                user_response = "SKIP" # Treat EOF as skip

            if user_response.upper() == 'SKIP':
                print("Skipping cover image generation.")
                cover_image_data = None # Ensure no cover image is saved
                cover_error = None # Break the loop
            else:
                print("Retrying cover image generation with revised prompt...")
                cover_prompt = user_response # Update the prompt
                cover_image_data, cover_error = generate_image_from_prompt(
                    prompt_text=cover_prompt,
                    size="1536x1024",
                    quality="high"
                )
                # Loop continues if cover_error is still present after retry

        # --- Save Cover Image (if successful or not skipped) ---
        if cover_image_data:
            cover_filename = os.path.join(book_dir, "cover.png")
            try:
                with open(cover_filename, "wb") as f:
                    f.write(cover_image_data)
                print(f"Cover image saved successfully as {cover_filename}")
            except IOError as e:
                print(f"Error saving cover image {cover_filename}: {e}")

    except KeyError as e:
        print(f"Error accessing cover prompt template key in prompts.json: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during cover generation: {e}")


    # --- Loop through pages, maintaining history and potentially previous image ---
    print("\n--- Starting Page Generation ---")
    all_pages_successful = True
    message_history = [] # Initialize empty history
    previous_page_image_data = None # Initialize variable to store previous image data

    for page_num in range(1, total_pages + 1): # Use dynamic total_pages
        progress_percent = int((page_num / total_pages) * 100)
        print(f"\n===== Processing Page {page_num}/{total_pages} ({progress_percent}%) =====")

        # --- Stage 1: Generate Single Page Structure ---
        print(f"--- Running Stage 1: Generating Structure for Page {page_num}... ---")
        # Pass the chosen style type to determine which Stage 1 prompt to use
        style_type = chosen_style.get('type', 'childrens') # Default to 'childrens' if type is missing
        page_data, updated_history, error1 = generate_single_page_structure(
            characters, story_outline, page_num, message_history, total_pages, style_type=style_type
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

        # Extract the correct text based on style type
        scene_desc = page_data.get("scene_description", "")
        if style_type == "narrative":
            page_content_text = page_data.get("script_text", "") # Expect script_text for narrative
            text_key_for_image = "script_text"
        else: # childrens
            page_content_text = page_data.get("page_text", "") # Expect page_text for childrens
            text_key_for_image = "page_text"

        if not page_content_text:
             print(f"Warning: No '{text_key_for_image}' found in Stage 1 output for page {page_num}.")
             # Decide if we should continue without text or mark as error? Let's continue for now.
             # page_content_text = "" # Ensure it's an empty string if missing

        print(f"--- Stage 1 Success for Page {page_num}. ---")

        # --- Stage 2: Generate or Edit Image ---
        print(f"--- Running Stage 2: Generating/Editing Image for Page {page_num}... ---")

        # Find characters mentioned in this scene's description
        mentioned_chars = {
            name: desc for name, desc in characters.items()
            if name.lower() in scene_desc.lower()
        }
        char_details_string = "\n".join([f"- {name}: {desc}" for name, desc in mentioned_chars.items()])
        if not char_details_string:
             char_details_string = "(No specific characters mentioned in scene description)"

        # Format the image prompt using the CHOSEN style template
        try:
            # Use the key selected by the user
            img_prompt_template = PROMPTS[chosen_style['key']]['prompt_template']
            # Use the correct text variable (page_text or script_text) based on the key expected by the template
            # We'll pass both, but the template should only use one ({page_text} or {script_text})
            image_prompt = img_prompt_template.format(
                scene_description=scene_desc,
                character_details_string=char_details_string,
                page_text=page_content_text if text_key_for_image == "page_text" else "", # Pass relevant text or empty
                script_text=page_content_text if text_key_for_image == "script_text" else "" # Pass relevant text or empty
            )
        except KeyError as e:
            # Check if the error is due to the template expecting a key that wasn't generated
            if str(e) == text_key_for_image:
                 print(f"Error: Image prompt template '{chosen_style['key']}' expects '{{{text_key_for_image}}}' but it was missing in Stage 1 output for page {page_num}.")
            else:
                 print(f"Error: Could not find key '{str(e)}' when formatting image prompt for page {page_num}. Check prompts.json.")
            print(f"Error: Could not find '{chosen_style['key']}' or 'prompt_template' in prompts.json for page {page_num}")
            all_pages_successful = False
            continue
        except Exception as e:
             print(f"Error formatting image prompt for page {page_num}: {e}")
             all_pages_successful = False
             continue

        # --- Generate or Edit Image based on mode and page number ---
        image_data = None
        error2 = None

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
    print("\n--- Book Generation Finished ---")
    if all_pages_successful:
        print("All pages processed successfully!")
    else:
        print("Some pages may have encountered errors during generation or saving.")
    print(f"Your book pages are located in: {book_dir}")
    print(f"Total time taken: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    main()
