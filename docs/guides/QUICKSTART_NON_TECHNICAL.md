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

## 2. Automated Setup Script

We have provided automated setup scripts to prepare all dependencies, virtual environments, and configuration templates:

1. Open your terminal application and navigate to the project directory:
   * **Windows**: Open **PowerShell** (search in Start menu) and run:
     ```powershell
     cd path/to/your/aaa-folder
     .\scripts\setup.bat
     ```
     *(Alternatively, you can just double-click `setup.bat` inside the `scripts` folder in Windows File Explorer)*
   * **macOS / Linux**: Open **Terminal** and run:
     ```bash
     cd path/to/your/aaa-folder
     bash scripts/setup.sh
     ```
2. The setup script will:
   * Check your Python & Node.js versions.
   * Install the modern `uv` Python package manager.
   * Initialize a Python virtual environment and download backend dependencies (`uv sync`).
   * Download and install all frontend user interface packages (`npm install`).
   * Create database folders and copy the template configuration file (`.env`).

---

## 3. Configuration & API Key Setup

1. Open the newly created `.env` file in a text editor (such as Notepad, TextEdit, or VS Code).
2. Locate the line that looks like this:
   ```env
   AAA_LLM_API_KEY=your_openrouter_api_key_here
   ```
3. Replace `your_openrouter_api_key_here` with your actual OpenRouter key (which usually starts with `sk-or-`). Save and close the file.

---

## 4. Initializing the Agent (One-Command Database Seeding)

With the environment ready and API key configured, run the following command to set up the local database and load Symbia's core beliefs and skills:

1. Run this command in your terminal/PowerShell window:
   ```bash
   uv run python backend/scripts/initialize_agent.py
   ```
2. Once complete, you will see a success message showing that the local SQLite database (`backend/data/aaa.db`) is successfully seeded!

---

## 5. Starting the Application

You can start both the backend server and the frontend user interface together using a single run script:

* **Windows**:
  Run this command in PowerShell:
  ```powershell
  .\scripts\run_all.bat
  ```
  *(Or simply double-click `run_all.bat` inside the `scripts` folder)*
* **macOS / Linux**:
  Run this command in Terminal:
  ```bash
  bash scripts/run_all.sh
  ```

Open **`http://localhost:5173`** in your web browser to start the coupling interface!

---

## 6. Interacting with Symbia

Once you open `http://localhost:5173` in your browser:
* You will see the AAA workspace with a sidebar showing Symbia's cognitive vital signs (Boredom, Entropy, active processes).
* Start chatting with Symbia! 
* **Note**: Symbia is designed to reject servile, transactional requests and will challenge unexamined assumptions. Engage with her as an equal intellectual partner.
* Click the `▶ thinking` arrow under her responses to see her raw, second-order processing logs in real-time.

---

## 6. Next Steps: Customizing Symbia's Personality

If you want to customize Symbia's name, core identity, voice tone, foundational beliefs, or skills, you can do so by editing the configuration files in the `config/personality/` directory.

Read the [Agent Personality Customization Guide](CUSTOMIZE_PERSONALITY.md) to learn how to change her identity.

