
# alright, first things first, gotta pull in the tools we need
import google.generativeai as genai # this one's for the AI brain power, the gemini stuff
import os # need this for file stuff, like checking if a file exists, ya know? operating system interactions
from dotenv import load_dotenv # this helps us load secret stuff like API keys from a special file (.env) so we dont plaster it everywhere
import subprocess # lets us run commands on the computer, like actually DOING things in the terminal
import datetime # for timestamping things, like in the log file
import sys # needed for exiting the script cleanly like saying 'bye Felicia!' to the program

#========================================================================
# COLOR time!! Make the terminal look pretteh
# definin' some fancy colors so the output isn't boring black and white
red = "\033[91m"         # for errors and stuff, make it POP
green = "\033[32m"       # success messages, lookin' good
blue = "\033[94m"        # informational things, maybe?
purple = "\033[95m"      # just another cool color
gold = "\033[38;5;220m"  # ooh, fancy gold!
cyan = "\033[36m"        # light blue, nice n calm
yellow = "\033[93m"      # Adding yellow for warnings
reset = "\033[0m"        # IMPORTANT: gotta reset the color back to normal, or everything stays colored!
#========================================================================

# Function to check if we have that .env file with the API key
# tries to be smart about loading the key
def load_api_key():
    """Check if .env exists n load the API key, otherwise bug the user for it."""
    if os.path.exists(".env"):
        print(f"{blue}Found the .env file, nice! Lemme see if the key's in there...{reset}")
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            print(f"{green}Got the API key from .env! Ready to roll.{reset}")
            return api_key
        else:
            print(f"{red}Hmm, found .env but no GEMINI_API_KEY in it. Please enter the key manually.{reset}")
            api_key = prompt_for_api_key()
            return api_key
    else:
        print(f"{blue}No .env file found. No worries, let's make one and save your API key.{reset}")
        api_key = prompt_for_api_key()
        return api_key

# This little helper function asks the user for the key and saves it
def prompt_for_api_key():
    """Asks the user prettily for their Gemini API key and saves it to .env."""
    api_key = input(f"{green}Please paste your Gemini API key here: {reset}").strip()
    with open(".env", "w") as file:
        file.write(f"GEMINI_API_KEY={api_key}\n")
    print(f"{gold}Alrighty, API key saved in .env! You won't have to enter it again (unless it changes).{reset}")
    return api_key

# === Part 1: Setting up the AI ===
api_key = load_api_key()
# Configure the genai library, adding safety settings to reduce harmful content generation
try:
    genai.configure(api_key=api_key)
    # Create the model instance once here if possible, reduces overhead
    # Using a slightly more robust model potentially, adjust if needed
    model = genai.GenerativeModel("gemini-1.5-flash-latest")
    print(f"{green}AI Model configured successfully with safety settings.{reset}")
except Exception as config_err:
    print(f"{red}Fatal Error configuring the AI Model: {config_err}{reset}")
    print(f"{red}This might be due to an invalid API key or network issues.{reset}")
    sys.exit(1) # Exit if we can't configure the AI

# === Part 2: The Magic Prompts ===

# *MODIFIED* base_prompt to ask for command AND explanation
base_prompt = """
You are an AI assistant that generates Windows CLI commands.
Analyze the user's request: {INPUT}

Follow these rules STRICTLY:
1. Provide the necessary Windows CLI command on the FIRST line. Assume all required tools/apps are available.
2. On the SECOND line, provide a SINGLE, concise sentence explaining what the command does. Start this line exactly with "Explanation: ".
3. Generate ONLY the command and the explanation line. NOTHING else before or after. No greetings, no extra comments, no warnings here.
4. Keep the command as simple as possible unless specific options are requested by the user.
5. For compound commands (using pipes |, operators &&, etc.), provide the complete command on the single first line.
6. Only ONE command variation.

Example Request: list files in current directory
Example Response:
dir
Explanation: Lists files and folders in the current directory.

Example Request: delete the temp file named report.tmp
Example Response:
del report.tmp
Explanation: Deletes the specified file 'report.tmp'.
"""

# *NEW* Prompt for the risk validation function
risk_check_prompt = """
Analyze the potential risk of executing the following Windows command:
`{COMMAND}`
Is this command potentially risky or destructive (e.g., irreversible data deletion, system modification, formatting, requires elevation)?
- If YES, respond ONLY with the format: "Risky: [Explain the specific risk briefly in one sentence]". Example: "Risky: This command permanently deletes files without confirmation."
- If NO, respond ONLY with the exact text: "Safe".
Do not add any other text, greetings, or explanations. Focus solely on risk assessment.
"""

# *NEW* Function to validate command risk using the AI
def validate_command_risk(command_to_check):
    """Asks the AI if a given command is risky and returns the risk explanation or None."""
    if not command_to_check:
        return None # Cannot validate an empty command

    try:
        prompt = risk_check_prompt.replace("{COMMAND}", command_to_check)
        # Use the same configured model
        response = model.generate_content(prompt)

        if response and response.text:
            response_text = response.text.strip()
            if response_text.startswith("Risky:"):
                # Extract the explanation part after "Risky: "
                return response_text[len("Risky:"):].strip()
            elif response_text == "Safe":
                return None # Command is considered safe
            else:
                # Unexpected response from the risk check prompt
                print(f"{yellow}Warning: Unexpected response during risk check: {response_text}{reset}")
                return None # Treat unexpected response as non-risky for safety, or handle differently if needed
        else:
            print(f"{yellow}Warning: Could not get a risk assessment response from the AI.{reset}")
            return None # Treat no response as non-risky

    except Exception as e:
        print(f"{red}Error during command risk validation: {e}{reset}")
        # In case of error, maybe default to treating as potentially risky or just skip check?
        # For now, let's return None (treat as not explicitly risky) but log the error.
        return None

# *MODIFIED* Function that takes the user's wish and gets the command AND explanation from Gemini
def gemini_command_and_explanation(user_input):
    """Takes user input, gets command and explanation from AI, returns (command, explanation, error_message)."""
    try:
        if not user_input.strip():
            return None, None, f"{red}Whoops, looks like you didn't type anything! Try again?{reset}"

        prompt = base_prompt.replace("{INPUT}", user_input)
        # Use the pre-configured model
        response = model.generate_content(prompt)

        # Check for valid response and text
        if response and response.text and response.text.strip():
            response_text = response.text.strip()
            lines = response_text.split('\n', 1) # Split into max 2 parts (command and maybe explanation)

            command = lines[0].strip()
            explanation = ""

            if len(lines) > 1 and lines[1].strip().startswith("Explanation:"):
                explanation = lines[1].replace("Explanation:", "", 1).strip() # Use replace with count 1
            elif len(lines) == 1:
                 print(f"{yellow}Warning:{reset} AI only provided the command, no explanation line found.{reset}")
                 # Optionally, you could make another call here to get just the explanation, but let's keep it simple for now.
            else:
                 print(f"{yellow}Warning:{reset} AI response format might be unexpected. Got:\n{response_text}{reset}")
                 # Still try to return the first line as command if possible

            if not command: # If the first line (command) is empty, it's an error
                return None, None, f"{red}AI response did not contain a command.{reset}"

            return command, explanation, None # Return command, explanation, and None for error

        else:
            # Handle cases where the response might be blocked by safety settings or is empty
            try:
                 # Try to access prompt_feedback if available
                 feedback = response.prompt_feedback
                 block_reason = feedback.block_reason if feedback else "Unknown"
                 print(f"{red}Error: AI response blocked or empty. Reason: {block_reason}{reset}") # Log the raw response for debugging
            except Exception:
                 print(f"{red}Error: AI response was empty or invalid.{reset}") # Log the raw response for debugging

            return None, None, f"{red}AI seemed to have a moment... couldn't generate a command. Maybe try phrasing differently or check safety settings?{reset}"

    except Exception as e:
        print(f"{red}Uh oh, ran into an error talking to the AI: {e}{reset}")
        # Check for specific API errors if possible
        if "API key not valid" in str(e):
             print(f"{red}Please check if your GEMINI_API_KEY is correct in the .env file.{reset}")
        return None, None, f"{red}Something went wrong trying to get the command. Check the error message above?{reset}"


# Function to ask the AI to explain stuff (remains mostly the same)
def explain_command(command_input):
    """Asks the AI to explain a command or concept simply."""
    try:
        prompt = f"Explain this Windows command or related concept in a simple, easy-to-understand way, like explaining it to a friend: {command_input}"
        # Use the pre-configured model
        response = model.generate_content(prompt)
        if response and response.text:
             return response.text.strip()
        else:
             return f"{red}Couldn't get an explanation for that. The AI might be stumped or the response was empty.{reset}"
    except Exception as e:
        print(f"{red}Dang, error trying to get an explanation: {e}{reset}")
        return f"{red}Couldn't get an explanation due to an error.{reset}"

# Lets load some custom shortcuts (aliases) if the user made any
def load_aliases():
    """Loads user-defined aliases from a '.px_aliases' file if it exists."""
    aliases = {}
    alias_file = ".px_aliases" # Define filename
    if os.path.exists(alias_file):
        print(f"{blue}Found {alias_file}! Loading custom shortcuts...{reset}")
        try:
            with open(alias_file, "r") as file:
                for i, line in enumerate(file):
                     line = line.strip()
                     if line and not line.startswith("#"):
                         parts = line.split("=", 1)
                         if len(parts) == 2:
                             name = parts[0].strip()
                             value = parts[1].strip()
                             if name: # Ensure alias name is not empty
                                 aliases[name] = value
                                 print(f"  - Loaded alias: {name}")
                             else:
                                 print(f"{yellow}Warning: Skipped line {i+1} in {alias_file} due to empty alias name.{reset}")
                         else:
                             print(f"{yellow}Warning: Skipped invalid line {i+1} in {alias_file} (format: alias_name=command): {line}{reset}")
        except Exception as e:
             print(f"{red}Error loading aliases from {alias_file}: {e}{reset}")
    else:
        print(f"{blue}No {alias_file} file found. You can create one (e.g., !logs=dir C:\\logs).{reset}")
    return aliases

# --- Load em up! ---
aliases = load_aliases()

# The fancy welcome screen!
banner = fr""" {green}
##################################################
#     _    _        ____ __  __ ____      __  __ #
#    / \  (_)      / ___|  \/  |  _ \     \ \/ / #
#   / _ \ | |_____| |   | |\/| | | | |_____\  /  #
#  / ___ \| |_____| |___| |  | | |_| |_____/  \  #
# /_/   \_\_|      \____|_|  |_|____/     /_/\_\ #
#                                                #
##################################################{reset}
        {blue}Developed by Muhammad Izaz Haider{reset}
      {gold}Your personal AI-powered CMD assistant{reset}
{reset}
"""
print(banner)

# Function to let the user pick a mode: quick or interactive
def mode_selection():
    """Asks the user to choose between quick (run now) or interactive (ask first) mode."""
    while True:
        print(f"{purple}Select Operating Mode:{reset}")
        # Added clarification about risk assessment
        print(f"{gold}[1] Quick Mode{reset}{blue}\t\t(Commands run after AI risk check & your confirmation if risky){reset}")
        print(f"{gold}[2] Interactive Mode{reset}  {blue}(Shows command/explanation/risk, then asks to run/copy/cancel){reset}")
        print(f"{gold}[3] Exit{reset}{blue}\t\t(Quit the application){reset}")
        choice = input(f"{green}\nEnter your choice (1, 2, or 3): {reset}").strip()
        if choice == "1":
            return "quick"
        elif choice == "2":
            return "interactive"
        elif choice == "3":
            print(f"{red}Okay, exiting Ai-CMD-X. Catch ya later!{reset}")
            sys.exit()
        else:
            print(f"{red}Heh, '{choice}' isn't one of the options. Try again with 1, 2, or 3.{reset}\n")

# Function to execute the command and handle output/logging
def run_command_safely(command, mode, user_input_for_log):
    """Executes the command, streams output, checks for admin issues, and logs."""
    print(f"{gold}\n~ Attempting to run command... fingers crossed!{reset}\n{cyan}--- Command Output Start ---\n{reset}")
    output_log = ""
    process = None # Initialize process to None
    try:
        # Use Popen for better control and streaming output
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True, encoding='utf-8', errors='replace')

        # Read and print output line by line
        for line in process.stdout:
            print(line, end="")
            output_log += line

        process.wait() # Wait for the command to complete
        print(f"{cyan}\n--- Command Output End ---{reset}") # Add newline for clarity

        # Check exit code
        if process.returncode != 0:
             print(f"{yellow}Warning: Command exited with code {process.returncode}.{reset}")

        # Check for common permission errors in output
        output_lower = output_log.lower()
        if "access is denied" in output_lower or "administrator privileges" in output_lower or "requires elevation" in output_lower:
            print(f"\n{red}!! Heads up: Looks like that command might need Administrator powers.{reset}")
            print(f"{red}!! Try running this script again as an Administrator if it didn't work.{reset}")

        # Log successful execution
        try:
            with open("history.log", "a", encoding='utf-8') as log_file:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_file.write(f"[{timestamp}] Mode: {mode}, Request: '{user_input_for_log}', Ran: '{command}'\n")
        except Exception as log_e:
            print(f"{red}Minor issue: Couldn't write to history.log file. Error: {log_e}{reset}")

    except FileNotFoundError:
         # Extract the base command name for a clearer error message
         base_cmd = command.split()[0] if command else "the command"
         print(f"{red}Error: The command '{base_cmd}' wasn't found on your system. Is it installed and in your PATH?{reset}")
    except subprocess.TimeoutExpired:
         print(f"{red}Error: The command timed out.{reset}")
         if process: process.kill() # Terminate the timed-out process
    except Exception as run_err:
        print(f"{red}Oof, error occurred while *running* the command: {run_err}{reset}")
        print(f"{red}The command was: {purple}{command}{reset}")


# ==================
# The MAIN Loop!
# ==================
while True:
    mode = mode_selection()
    print(f"\n{cyan}Okay, {reset}{gold}{mode.capitalize()}{reset} {cyan} Mode activated. Enter your request or type 'back'/'quit'.{reset}")

    while True:
        # Get user input
        print(f"{green}\nAi-CMD-X ({mode})> {reset}", end="") # Changed prompt slightly
        user_input = input().strip()

        # Handle control commands
        if not user_input: # Skip empty input
             continue
        if user_input.lower() in ["quit", "exit"]:
            print(f"\n{red}Alright, shutting down Ai-CMD-X. Hope it was helpful!{reset}")
            sys.exit()
        if user_input.lower() == "back":
            print(f"{blue}\n~ Okay, going back to mode selection...\n{reset}")
            break # Breaks inner loop, goes back to mode_selection()

        # Handle explanation requests
        if user_input.lower().startswith(("explain ", "what is ", "what's ")):
            print(f"{blue}You want an explanation for '{user_input}'? Let me ask the AI...{reset}")
            explanation_text = explain_command(user_input)
            print(f"{gold}\nAI Explanation:\n{reset}{explanation_text}{reset}")
            continue # Ask for next input

        # Handle aliases
        original_request = user_input # Keep original request for logging
        if user_input.startswith("!") and user_input[1:] in aliases:
            alias_name = user_input[1:]
            user_input = aliases[alias_name]
            print(f"{blue}~ Used alias '!{alias_name}' -> Translating request to: '{user_input}'{reset}")
            # Note: The user_input is now the command itself, AI won't be called for command generation.
            # We might want to skip AI generation and go straight to risk check/execution for aliases,
            # OR let the AI process the *expanded* command for consistency?
            # Let's proceed to AI generation with the expanded command for now, it might refine it.

        # --- Get Command and Explanation from AI ---
        print(f"{blue}\nOkay, asking the AI for a command and explanation for '{user_input}'...{reset}")
        command, explanation, error_msg = gemini_command_and_explanation(user_input)

        if error_msg:
            print(error_msg) # Print the specific error from the function
            continue # Ask for next input

        if not command: # Should be caught by error_msg, but double check
            print(f"{red}AI failed to provide a command. Please try again.{reset}")
            continue

        # --- Risk Validation Step ---
        print(f"{cyan}Checking command for potential risks...{reset}")
        risk_explanation = validate_command_risk(command)

        # --- Display Suggested Command, Explanation, and Risk ---
        print(f"\n{gold} AI Suggests:{reset}")
        print(f" Command:  {purple}{command}{reset}") # Display command
        
        if explanation:
             print(f" {cyan}Explanation: {explanation}{reset}") # Display explanation
             
        if risk_explanation:
            # Display risk warning prominently
  
            print(f"{yellow}\n!! {red}WARNING: POTENTIALLY RISKY COMMAND DETECTED!{reset}{yellow} !!{reset}")
            print(f"{gold}!! Risk:{reset} {risk_explanation}{reset}")



        # --- Mode-Dependent Action ---

        # QUICK MODE: Run immediately IF NOT RISKY, otherwise CONFIRM
        if mode == "quick":
            if risk_explanation:
                # Ask for confirmation BECAUSE it's risky
                confirm_risk = input(f"{red}\n This command is flagged as risky. Execute anyway? (y/n): {reset}").strip().lower()
                if confirm_risk in ['y', 'yes']:
                    print(f"{blue}Proceeding with risky command based on your confirmation.{reset}")
                    run_command_safely(command, mode, original_request)
                else:
                    print(f"{gold}~ Risky command execution cancelled by user.{reset}")
                    # No logging here as it wasn't run
            else:
                # Not risky, run immediately in Quick mode
                print(f"{gold}\n (Quick Mode)...{reset}")
                run_command_safely(command, mode, original_request)

        # INTERACTIVE MODE: Always ask user (run, copy, cancel)
        elif mode == "interactive":
            # Ask the user what they wanna do: run, cancel, or copy
            action = input(f"{green}\nAction? (y/yes=Run, c/copy=Copy, n/no=Cancel): {reset}").strip().lower()

            if action in ["c", "copy"]:
                try:
                    # Use powershell's Set-Clipboard for potentially better compatibility
                    subprocess.run(['powershell', '-Command', f'Set-Clipboard -Value "{command.replace("\"", "`\"")}"'], check=True, shell=True)
                    # Escaping quotes might be needed depending on command complexity
                    # os.system(f"echo {command.strip()} | clip") # Old method, might fail with complex commands
                    print(f"{green}\n~ Command copied to clipboard!{reset}")
                except Exception as e:
                    print(f"{red}Couldn't copy to clipboard automatically. Error: {e}{reset}")
                    print(f"{red}You can still copy it manually: {purple}{command}{reset}")
                # continue: In interactive mode, after copy/cancel/error, always go back to ask for new input

            elif action in ["n", "no", "cancel"]:
                print(f"{gold}\n~ Command cancelled.{reset}")
                # continue

            elif action in ["y", "yes", "run"]:
                # User confirmed execution
                run_command_safely(command, mode, original_request)

            else: # Unrecognised option
                print(f"{gold}Unrecognised option ('{action}'). Cancelling command.{reset}")
                # continue

# This part of the script is technically unreachable because of the infinite loops
# and sys.exit(), but it's good practice that the script *could* end if loops were different.
    print("Exiting Ai-CMD-X.")

