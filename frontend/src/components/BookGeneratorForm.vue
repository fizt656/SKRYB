<script setup lang="ts">
import { ref } from 'vue';

// Reactive variables for form inputs
const bookTitle = ref('');
const selectedStyle = ref(''); // Will store the key of the selected style
const numberOfPages = ref(10); // Default to 10 pages
const quickMode = ref(true); // Default to Quick Mode
const characterDescriptions = ref(''); // For Full Mode
const storyOutline = ref(''); // For both modes
const useExperimentalConsistency = ref(false);

// Placeholder for available styles (will need to fetch this from backend later)
const availableStyles = [
  { key: 'stage2_image_childrens', desc: 'Dreamy Childrens Book' },
  { key: 'stage2_image_dark_anime', desc: 'Dark Anime SciFi' },
  { key: 'stage2_image_dreamy_anime', desc: 'Dreamy Anime' },
  { key: 'stage2_image_70s_cartoon', desc: '70s Funky Cartoon' },
  { key: 'stage2_image_mgs_comic', desc: 'MGS Comic Book Style' },
  { key: 'stage2_image_cinematic_film_still', desc: 'Realistic Cinematic Film Still' }
];

// Function to handle form submission
const generateBook = async () => {
  const formData = {
    bookTitle: bookTitle.value,
    selectedStyle: selectedStyle.value,
    numberOfPages: numberOfPages.value,
    quickMode: quickMode.value,
    characterDescriptions: quickMode.value ? null : characterDescriptions.value, // Send null if in Quick Mode
    storyOutline: storyOutline.value,
    useExperimentalConsistency: useExperimentalConsistency.value
  };

  try {
    const response = await fetch('http://localhost:8000/generate-book', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(formData),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`HTTP error! status: ${response.status}, Details: ${errorData.detail}`);
    }

    const result = await response.json();
    console.log('Backend response:', result);
    alert('Book generation started. Check the backend terminal for progress updates.');
    // TODO: Handle backend response and show progress/results in the UI
  } catch (error: any) {
    console.error('Error sending book generation request:', error);
    alert(`Error sending book generation request: ${error.message}`);
  }
};
</script>

<template>
  <div class="book-generator-form">
    <h2 class="form-title">Generate Your Book</h2>

    <div class="form-group">
      <label for="bookTitle">Book Title:</label>
      <input type="text" id="bookTitle" v-model="bookTitle" required />
    </div>

    <div class="form-group">
      <label for="style">Illustration Style:</label>
      <select id="style" v-model="selectedStyle" required>
        <option value="" disabled>Select a style</option>
        <option v-for="style in availableStyles" :key="style.key" :value="style.key">
          {{ style.desc }}
        </option>
      </select>
    </div>

    <div class="form-group">
      <label for="numberOfPages">Number of Pages:</label>
      <input type="number" id="numberOfPages" v-model.number="numberOfPages" min="1" required />
    </div>

    <div class="form-group">
      <label>Generation Mode:</label>
      <div class="radio-group">
        <label>
          <input type="radio" value="true" v-model="quickMode" /> Quick Mode
        </label>
        <label>
          <input type="radio" value="false" v-model="quickMode" /> Full Mode
        </label>
      </div>
    </div>

    <div class="form-group" v-if="!quickMode">
      <label for="characterDescriptions">Character Descriptions (JSON format):</label>
      <textarea id="characterDescriptions" v-model="characterDescriptions" rows="4"></textarea>
      <small>Example: {"Character Name": "Description", "Another Character": "Description"}</small>
    </div>

    <div class="form-group">
      <label for="storyOutline">Story Outline/Concept:</label>
      <textarea id="storyOutline" v-model="storyOutline" rows="6" required></textarea>
    </div>

    <div class="form-group checkbox-group">
      <input type="checkbox" id="experimentalConsistency" v-model="useExperimentalConsistency" />
      <label for="experimentalConsistency">Enable Experimental Consistency Mode</label>
    </div>

    <button @click="generateBook" class="generate-button">Generate Book</button>
  </div>
</template>

<style scoped>
.book-generator-form {
  max-width: 600px;
  margin: 0 auto;
  padding: 2rem;
  background-color: var(--color-background-soft); /* Use a soft background */
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.form-title {
  color: var(--color-heading);
  text-align: center;
  margin-bottom: 1.5rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: var(--color-text);
  font-weight: bold;
}

.form-group input[type="text"],
.form-group input[type="number"],
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 0.8rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
  box-sizing: border-box; /* Include padding and border in element's total width and height */
}

.form-group textarea {
  resize: vertical; /* Allow vertical resizing */
}

.radio-group label {
  display: inline-block;
  margin-right: 1rem;
  font-weight: normal;
}

.checkbox-group {
  display: flex;
  align-items: center;
}

.checkbox-group input[type="checkbox"] {
  margin-right: 0.5rem;
}

.generate-button {
  display: block;
  width: 100%;
  padding: 1rem;
  background-color: #ffc107; /* Warm yellow from logo */
  color: #333; /* Dark text for contrast */
  border: none;
  border-radius: 4px;
  font-size: 1.1rem;
  font-weight: bold;
  cursor: pointer;
  transition: background-color 0.3s ease, box-shadow 0.3s ease;
}

.generate-button:hover {
  background-color: #ffda6a; /* Lighter yellow on hover */
  box-shadow: 0 4px 12px rgba(255, 193, 7, 0.4); /* Subtle glow effect */
}

/* Basic dark mode adjustments (inherits from global styles) */
/* Add specific overrides here if needed */
</style>
