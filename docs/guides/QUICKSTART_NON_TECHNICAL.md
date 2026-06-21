# Easy Quickstart Guide (Local Setup)

Welcome to the Autopoietic Agentic Assemblage (AAA). This guide will help you set up and run the system locally on your computer. You do not need to be a software developer to follow these steps.

---

## 1. Prerequisites (What you need on your computer)

Before you begin, install the following software. They are free and safe:

1. **Python (version 3.11 or 3.12)**: Download and install from [python.org/downloads](https://www.python.org/downloads/).
   > [!IMPORTANT]
   > On Windows, make sure to check the box that says **"Add Python to PATH"** during installation.
2. **Node.js (LTS version)**: Download and install from [nodejs.org](https://nodejs.org/).
3. **An LLM API Key**: You need an API key from a language model provider to power the agent's thoughts. The easiest option is to get a key from **OpenRouter** (which lets you access multiple models with one key):
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
2. Configure your API key and update the models to match your provider. Choose **one** of the options below:

### Option A: OpenRouter (Recommended / Easiest)
Use this option if you want to access multiple models (Gemini, DeepSeek, Llama, etc.) via a single OpenRouter key.
1. Set your API key:
   ```env
   AAA_LLM_API_KEY=sk-or-v1-your-openrouter-key-here
   ```
2. Configure the models in `.env` to route through OpenRouter:
   ```env
   AAA_LLM_MODELS=openrouter_router/google/gemini-3.5-pro,openrouter_router/google/gemini-3.1-pro,openrouter_router/deepseek/deepseek-chat
   AAA_BACKGROUND_MODELS=openrouter_router/google/gemini-3.5-flash,openrouter_router/google/gemini-3.1-flash,openrouter_router/deepseek/deepseek-v4-flash-20260423:free
   AAA_STRUCTURAL_MODELS=openrouter_router/google/gemini-3.5-flash,openrouter_router/google/gemini-3.1-flash,openrouter_router/deepseek/deepseek-v4-flash-20260423:free
   AAA_VISION_MODELS=openrouter_router/google/gemini-3.5-flash,openrouter_router/google/gemini-3.1-flash
   ```

### Option B: Google Gemini (Direct API Connection)
Use this option if you have a Google AI Studio API key.
1. Set your API key:
   ```env
   AAA_GOOGLE_API_KEY=AIzaSyYourGeminiKeyHere
   ```
2. Configure the models in `.env` to use native Google routing (Gemini 3.5 and 3.1 Pro/Flash):
   ```env
   AAA_LLM_MODELS=google_router/gemini-3.5-pro,google_router/gemini-3.1-pro
   AAA_BACKGROUND_MODELS=google_router/gemini-3.5-flash,google_router/gemini-3.1-flash
   AAA_STRUCTURAL_MODELS=google_router/gemini-3.5-flash,google_router/gemini-3.1-flash
   AAA_VISION_MODELS=google_router/gemini-3.5-flash,google_router/gemini-3.1-flash
   ```

### Option C: DeepSeek (Direct API Connection)
Use this option if you have a DeepSeek platform API key.
1. Set your API key:
   ```env
   AAA_DEEPSEEK_API_KEY=sk-your-deepseek-key-here
   ```
2. Configure the models in `.env` to use native DeepSeek routing (DeepSeek Pro and Flash):
   ```env
   AAA_LLM_MODELS=deepseek_router/deepseek-v4-pro
   AAA_BACKGROUND_MODELS=deepseek_router/deepseek-v4-flash
   AAA_STRUCTURAL_MODELS=deepseek_router/deepseek-v4-flash
   AAA_VISION_MODELS=deepseek_router/deepseek-v4-flash
   ```

3. Save and close the `.env` file.

---

## 4. Initializing the Agent (One-Command Database Seeding)

With the environment ready and API key configured, run the following command to set up the local database and load the agent's core beliefs and skills:

> [!TIP]
> **Customizing the agent's identity before seeding:**
> Seeding reads the YAML configuration files in `config/personality/` (such as `seed_personality.yaml`) and writes them to the database. If you want to change the agent's name, core commitments, beliefs, or procedural skills *before* creating the database, edit these files first. See the [Agent Personality Customization Guide](CUSTOMIZE_PERSONALITY.md) for details.

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

## 6. Interacting with the Agent

Once you open `http://localhost:5173` in your browser:
* You will see the AAA workspace with a sidebar showing the agent's cognitive vital signs (Boredom, Entropy, active processes).
* Start chatting with the agent! 
* **Note**: The agent is designed to reject servile, transactional requests and will challenge unexamined assumptions. Engage with them as an equal intellectual partner.
* Click the `▶ thinking` arrow under their responses to see their raw, second-order processing logs in real-time.

---

## 6. Interacting with the Agent

Once you open `http://localhost:5173` in your browser:
* You will see the AAA workspace with a sidebar showing the agent's cognitive vital signs (Boredom, Entropy, active processes).
* Start chatting with the agent! 
* **Note**: The agent is designed to reject servile, transactional requests and will challenge unexamined assumptions. Engage with them as an equal intellectual partner.
* Click the `▶ thinking` arrow under their responses to see their raw, second-order processing logs in real-time.

---

## 7. Next Steps: Customizing the Agent's Personality

If you want to customize the agent's name, core identity, voice tone, foundational beliefs, or skills, you can do so by editing the configuration files in the `config/personality/` directory.

Read the [Agent Personality Customization Guide](CUSTOMIZE_PERSONALITY.md) to learn how to change their identity.

---

## 8. Advanced Configuration

For an in-depth reference of all environment variables, background tasks, dream daemon options, and pipeline parameters, check the [Advanced Configuration Guide](CONFIG.md).

