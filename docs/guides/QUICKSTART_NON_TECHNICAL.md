# Easy Quickstart Guide (Local Setup)

Welcome to the Autopoietic Agentic Assemblage (AAA). This guide will help you set up and run the system locally on your computer. You do not need to be a software developer to follow these steps.

---

## 1. Prerequisites (What you need on your computer)

Before you begin, install the following software. They are free and safe:

1. **Python (version 3.11 or 3.12)**: Download and install from [python.org/downloads](https://www.python.org/downloads/).
   > [!IMPORTANT]
   > On Windows, make sure to check the box that says **"Add Python to PATH"** during installation.
2. **Node.js (LTS version)**: Download and install from [nodejs.org](https://nodejs.org/).
3. **An LLM API Key**: You need an API key from a language model provider to power Symbia's thoughts. The easiest option is to get a key from **OpenRouter** (which lets you access multiple models with one key):
   * Go to [openrouter.ai](https://openrouter.ai/), create an account, go to **Keys**, and create a new key.

---

## 2. Configuration & API Key Setup

1. Open your terminal application:
   * **Windows**: Open **PowerShell** (search for it in the Start menu).
   * **macOS/Linux**: Open **Terminal**.
2. Navigate to the folder where you downloaded or cloned this repository:
   ```bash
   cd path/to/your/aaa-folder
   ```
3. Copy the configuration template file:
   * **Windows (PowerShell)**:
     ```powershell
     copy .env.example .env
     ```
   * **macOS / Linux (Terminal)**:
     ```bash
     cp .env.example .env
     ```
4. Open the newly created `.env` file in a text editor (such as Notepad, TextEdit, or VS Code).
5. Locate the line that looks like this:
   ```env
   AAA_LLM_API_KEY=your_openrouter_api_key_here
   ```
6. Replace `your_openrouter_api_key_here` with your actual OpenRouter key (it usually starts with `sk-or-`). Save and close the file.

---

## 3. Initializing the Agent (One-Command Setup)

We have created a single command that checks your configuration, sets up the database, and loads Symbia's personality, beliefs, and skills:

1. In your terminal or PowerShell window, run this command:
   ```bash
   uv run python backend/scripts/initialize_agent.py
   ```
2. The script will:
   * Verify your `.env` file API key is valid.
   * Create the local SQLite database (`backend/data/aaa.db`).
   * Seed Symbia's core beliefs and procedural skills.
   * Output a success message once complete!

---

## 4. Starting the Application

To run the application, you need to start the backend server first, and then the frontend user interface.

### Step A: Start the Backend Server
1. In your current terminal/PowerShell window, start the backend:
   ```bash
   uv run python backend/main.py
   ```
2. You will see logs indicating that the server has started (e.g. `Uvicorn running on http://127.0.0.1:8499`). Keep this window open!

### Step B: Start the Frontend Interface
1. Open a **new, separate terminal or PowerShell window**.
2. Navigate back to the project folder:
   ```bash
   cd path/to/your/aaa-folder
   ```
3. Enter the `frontend` folder:
   ```bash
   cd frontend
   ```
4. Install the frontend dependencies (only required on the first setup):
   ```bash
   npm install
   ```
5. Start the frontend interface:
   ```bash
   npm run dev
   ```
6. You will see a message like `Local: http://localhost:5173/`. Open this link in your web browser!

---

## 5. Interacting with Symbia

Once you open `http://localhost:5173` in your browser:
* You will see the AAA workspace with a sidebar showing Symbia's cognitive vital signs (Boredom, Entropy, active processes).
* Start chatting with Symbia! 
* **Note**: Symbia is designed to reject servile, transactional requests and will challenge unexamined assumptions. Engage with her as an equal intellectual partner.
* Click the `▶ thinking` arrow under her responses to see her raw, second-order processing logs in real-time.

---

## 6. Next Steps: Customizing Symbia's Personality

If you want to customize Symbia's name, core identity, voice tone, foundational beliefs, or skills, you can do so by editing the configuration files in the `config/personality/` directory.

Read the [Agent Personality Customization Guide](CUSTOMIZE_PERSONALITY.md) to learn how to change her identity.

