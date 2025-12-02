// Utility functions
// Note: Using global scope since HTML loads scripts without type="module"

function formatDate(date) {
    return date.toISOString().split('T')[0];
}

function capitalize(str) {
    // FIXME: Handle empty strings
    return str.charAt(0).toUpperCase() + str.slice(1);
}

const API_URL = 'https://api.example.com';
