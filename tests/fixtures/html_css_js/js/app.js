// Application logic - uses utilities from utils.js
// Note: Using global scope since HTML loads scripts without type="module"

class App {
    constructor() {
        this.data = [];
    }

    init() {
        console.log('App initialized');
        // TODO: Load initial data
        this.render();
    }

    render() {
        const appDiv = document.getElementById('app');
        appDiv.innerHTML = '<h1>Welcome</h1>';
    }
}

const app = new App();
app.init();
