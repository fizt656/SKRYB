# SKRYB

![SKRYB Logo](skryb_logo.png)

SKRYB uses OpenAI's and Replicate's APIs to generate illustrated books based on user-provided prompts and style choices.

## Features

*   Generates book pages sequentially, maintaining story context.
*   Creates a cover image based on the chosen style and characters.
*   **Dual AI Model Support**: Choose between OpenAI's Image-1 and Replicate's FLUX model for image generation.
*   **Dynamic Character Entry**: A user-friendly interface in "Full Mode" to easily add, edit, and remove characters without needing to write JSON.
*   **Experimental Style Reference**: When using the Replicate model, you can upload an image to be used as a style reference for the entire book.
*   **Replicate Safety Control**: Adjust the `safety_tolerance` for the Replicate model directly in the UI.
*   **Experimental Consistency Mode (OpenAI)**: An optional mode that uses the OpenAI Images API's edit endpoint for potentially better page-to-page consistency (so far it's a too strict to be usable for general style consistency, as it retains the composition of the reference).
*   **Future Feature: Character Image References:** A more advanced system to allow users to provide specific image references for each character using Flux Kontext might be a good idea later (right now it might be working for style, but not character consistency).

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/fizt656/SKRYB/
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows:
    # venv\Scripts\activate
    # On macOS/Linux:
    # source venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Set up API Keys:**
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Open the `.env` file and add your API keys for OpenAI and/or Replicate.

## Usage

SKRYB is used via the Web Graphical User Interface (GUI).

1.  **Start the Backend API:** Open a terminal in the project's root directory and run:
    ```bash
    uvicorn api:app --reload
    ```
2.  **Start the Frontend Development Server:** Open a *new* terminal instance, navigate to the `frontend` directory (`cd frontend`), and run:
    ```bash
    npm install
    npm run dev
    ```
    The frontend will typically be available at `http://localhost:5173/`.

Fill out the form in your browser to generate a book. The following options are available:

*   **Image Generation Model**: Choose between OpenAI's Image-1 model for high-quality, creative images or Replicate's FLUX Kontext model for a experimental use for now.
*   **Reference Image (Replicate Only)**: Optionally upload an image to be used as a style reference for the entire book.
*   **Safety Tolerance (Replicate Only)**: Control the content safety level for the Replicate model.
*   **Illustration Style**: Select from a list of predefined illustration styles to set the artistic tone of your book.
*   **Generation Mode**:
    *   **Quick Mode:** Provide a simple story concept, and the application will automatically infer the characters.
    *   **Full Mode:** Take full control by defining each character with a name and a detailed description using the dynamic character entry form.
*   **Experimental Consistency Mode (OpenAI Only)**: An optional mode that may improve character consistency between pages when using the OpenAI model.

Once you click "Generate Book," you can monitor the progress in the status log area at the bottom of the page.

## License

This project is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License. See the [LICENSE](LICENSE) file for details.
