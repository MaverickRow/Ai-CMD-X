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
reset = "\033[0m"        # IMPORTANT: gotta reset the color back to normal, or everything stays colored!
#========================================================================

# Function to check if we have that .env file with the API key

# tries to be smart about loading the key
def load_api_key():
    """Check if .env exists n load the API key, otherwise bug the user for it."""
    
    # does the '.env' file exist in the same folder?
    if os.path.exists(".env"):
        print(f"{blue}Found the .env file, nice! Lemme see if the key's in there...{reset}")
        load_dotenv()  # Load the secrets from .env file
        # ok, now try to get the specific key named "GEMINI_API_KEY"
        api_key = os.getenv("GEMINI_API_KEY")
        
        if api_key:
            # WOOHOO! got the key
            print(f"{green}Got the API key from .env! Ready to roll.{reset}")
            return api_key
        
        else:
            # Aww, .env file is there, but no key inside? Or maybe named wrong?
            print(f"{red}Hmm, found .env but no GEMINI_API_KEY in it. Please enter the key manually.{reset}")
            # gotta ask the user for it now
            api_key = prompt_for_api_key()
            return api_key
        
    else:
        # No .env file at all? Okay, time to create one.
        print(f"{blue}No .env file found. No worries, let's make one and save your API key.{reset}")
        # ask the user for the key
        api_key = prompt_for_api_key()
        return api_key

# This little helper function asks the user for the key and saves it
def prompt_for_api_key():
    """Asks the user prettily for their Gemini API key and saves it to .env."""
    
    # get the input, .strip() cleans up any accidental spaces at the start or end
    api_key = input(f"{green}Please paste your Gemini API key here: {reset}").strip()
    
    # now, write it into the .env file for next time
    # 'w' means write mode, it'll create the file if it doesnt exist or overwrite it if it does
    with open(".env", "w") as file:
        file.write(f"GEMINI_API_KEY={api_key}\n") # the \n makes sure theres a newline at the end, good practice
    print(f"{gold}Alrighty, API key saved in .env! You won't have to enter it again (unless it changes).{reset}")
    return api_key # send the key back to whoever called this function

# === Part 1: Setting up the AI ===
# Okay, let's actually GET the API key using our function above
api_key = load_api_key()

# now tell the genai library to use THIS key for all its magic
genai.configure(api_key=api_key) # configuration complete! hopefully.

# === Part 2: The Magic Prompt ===
# this is like the main instruction manual we give the AI *every* time
# we tell it exactly HOW we want it to respond. Less waffle, more command!
base_prompt = """
Provide me with the Windows CLI command necessary to complete the following request:
{INPUT}
Assume I have all necessary apps, tools, and commands necessary to complete the request.
Provide me with the command only and do not generate anything further. Like, seriously, JUST the command.
Do not provide any explanation. Nope. Nada. Zip.
Provide the simplest form of the command possible unless I ask for special options, considerations, output, etc. Keep it simple, buddy.
If the request does require a compound command (you know, like command1 | command2), provide all necessary operators, options, pipes, etc. as a single one-line command. ONE line.
Do not provide me more than one variation or more than one line. Just the one, please.
"""
# The {INPUT} part is where we'll slot in the user's actual request later on. Template magic!


# Function that takes the user's wish and gets the command from Gemini
def gemini_command(input):
    """Takes user input, plugs it into the prompt, and asks the AI for a command."""
    
    try:
        # first, check if the user actually typed something...
        if not input.strip(): # .strip() removes whitespace, so if it's empty after stripping...
            return f"{red}Whoops, looks like you didn't type anything! Try again?{reset}" # tell em off nicely

        # put the user's request into our template prompt
        prompt = base_prompt.replace("{INPUT}", input)
       
        # choose the AI model - 'gemini-1.5-flash-latest' is usually fast and good enough for this
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
       
        # okay, Moment of Truth: send the prompt to the AI!
        response = model.generate_content(prompt)

        # Did we get something back? And does it actually have text?
        if response and response.text.strip():
            # Success! Return the command text, stripped of any extra spaces
            return response.text.strip()
        
        else:
            # uh oh, AI gave us nothing back, or maybe an error we didnt catch?
            print(f"{red}Error: Response - {response}{reset}") # Log the raw response for debugging
            return f"{red}AI seemed to have a moment... couldn't generate a command. Maybe try phrasing differently?{reset}"
    
    except Exception as e:
        # Catch any other random errors during the API call
        print(f"{red}Uh oh, ran into an error talking to the AI: {e}{reset}")
        return f"{red}Something went wrong trying to get the command. Check the error message above?{reset}"

# Function to ask the AI to explain stuff
def explain_command(command_input):
    """Asks the AI to explain a command or concept simply."""
    
    try:
        # create a simple prompt asking for an explanation
        prompt = f"Explain this Windows command or related concept in a simple, easy-to-understand way, like explaining it to a friend: {command_input}"
       
        # same model as before, should be fine
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
       
        # ask the AI to explain
        response = model.generate_content(prompt)
       
        # return the explanation text
        return response.text.strip()
    
    except Exception as e:
        # if something goes wrong during explanation
        print(f"{red}Dang, error trying to get an explanation: {e}{reset}")
        return f"{red}Couldn't get an explanation for that. Maybe the AI is stumped too?{reset}" # return None maybe? Returning error message for now.

# Lets load some custom shortcuts (aliases) if the user made any
def load_aliases():
    """Loads user-defined aliases from a '.px_aliases' file if it exists."""
    
    aliases = {} # start with an empty dictionary to hold 'em
    # check if the alias file is present
    
    if os.path.exists(".px_aliases"):
        print(f"{blue}Found a .px_aliases file! Loading custom shortcuts...{reset}")
        
        # open the file for reading ('r')
        with open(".px_aliases", "r") as file:
           
            # read it line by line
            for line in file:
                # ignore empty lines or lines starting with # (comments)
                if line.strip() and not line.startswith("#"):
                    # split the line at the FIRST equals sign (=)
                   
                    name, value = line.strip().split("=", 1)
                    # store it in our dictionary, cleaning up spaces again
                   
                    aliases[name.strip()] = value.strip()
                    print(f"  - Loaded alias: {name.strip()}") # show what we loaded
    else:
        print(f"{blue}No .px_aliases file found. You can create one to add your own shortcuts like '!logs=dir C:\\logs'.{reset}")
    return aliases # return the dictionary of aliases (might be empty)

# --- Load em up! ---
aliases = load_aliases() # call the function to get our aliases ready

# The fancy welcome screen! ASCII art is funnnn.
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
    
    while True: # keep asking until they give a valid choice
        print(f"{purple}What’s our approach, you think?{reset}")
        print(f"{gold}[1] Quick Mode{reset}{blue}\t\t(Command runs INSTANTLY - Careful!) {reset}")
        print(f"{gold}[2] Interactive Mode{reset}  {blue}(I'll show you the command first, let you run, copy, or cancel){reset}")
        print(f"{gold}[3] Exit{reset}{blue}\t\t(Feeling done already?){reset}")
        choice = input(f"{green}\nEnter your choice (1, 2, or 3): {reset}").strip() # get their choice, strip spaces
       
        if choice == "1":
            return "quick" # return the mode name
       
        elif choice == "2":
            return "interactive" # return the mode name
       
        elif choice == "3":
            print(f"{red}Okay, exiting Ai-CMD-X. Catch ya later!{reset}")
            sys.exit() # cleanly exit the whole script
       
        else:
            # they typed something weird? tell 'em
            print(f"{red}Heh, '{choice}' isn't one of the options. Try again with 1, 2, or 3.{reset}\n")

# ==================
# The MAIN Loop! Where the action happens.
# ==================
while True: # This loop keeps running until the user explicitly exits (like with 'quit' or option 3)
    # First, figure out which mode the user wants to be in for this session
    mode = mode_selection()
  
    print(f"\n{cyan}Okay, {reset}{gold}{mode.capitalize()}{reset} {cyan} Mode is ON! Let's do this.{reset}")

    # This inner loop handles the requests *within* the chosen mode
    while True:
        # Ask the user what they want to do
        # the weird \033 stuff is just setting the color to cyan, then back to default after the input
        print(f"{green}\n~ What do you want to do? (or type back/quit) :{reset} ", end="")
        
        user_input = input().strip() # get the input, clean spaces

        # Check if they wanna bail completely
        if user_input.lower() in ["quit", "exit"]: # make it lowercase so Quit, quit, QUIT all work
            print(f"\n{red}Alright, shutting down Ai-CMD-X. Hope it was helpful!{reset}")
            sys.exit() # bye bye!

        # Check if they just want to go back to the mode selection screen
        if user_input.lower() == "back":
            print(f"{blue}\n~ Okay, going back to mode selection...{reset}")
            break # break out of *this* inner loop, goes back to the outer `while True` which calls mode_selection() again

        # Did they ask for an explanation? like "explain ping" or "what is cd"
        if user_input.lower().startswith("explain") or user_input.lower().startswith("what is"):
            print(f"{blue}You want an explanation for '{user_input}'? Let me ask the AI...{reset}")
            explanation = explain_command(user_input) # use our explain function
          
            if explanation: # did we get something back?
                print(f"{gold}\n AI Explanation: \n{reset}{explanation}{reset}") # show it nicely
            # after explaining, just loop back and ask for the next command/request
            continue # jumps to the start of the inner `while True` loop

        # Check if they used an alias (starts with '!')
        if user_input.startswith("!") and user_input[1:] in aliases:
            original_alias = user_input # keep the original for clarity maybe?
            user_input = aliases[user_input[1:]] # replace the alias with the actual command
            print(f"{blue}~ Used alias '{original_alias}' -> Translated to: '{user_input}'{reset}")

        # Okay, time to get the actual command from the AI!
        print(f"{blue}Okay, asking the AI how to '{user_input}'...{reset}")
        command = gemini_command(user_input) # call our gemini function

        # Check if we actually got a command back (it might have returned an error message)
        if not command or command.startswith(f"{red}"): # check if its None, empty, or starts with our red error color code
            print(f"{command}") # Print the error message we got back from gemini_command
            continue # go back and ask for input again

        # --- We have a command! ---
        # Show the user what the AI came up with
        print(f"\n{gold} AI Suggests: {reset} {purple}{command}{reset}\n")

        # --- Now, what to do depends on the mode ---

        # QUICK MODE: Just run it! YOLO!
        if mode == "quick":
            print(f"{blue}Running command immediately (Quick Mode)...{reset}")
            try:
                # subprocess.run just runs it and waits for it to finish. Simple.
                # shell=True is needed to run complex commands with pipes etc. Be a bit careful with this tho.
                subprocess.run(command, shell=True, check=False) # check=False means it won't raise an error if the command fails, it'll just print the error
           
            except Exception as e:
                # catch errors if the command itself is totally broken or something
                print(f"{red}Yikes! Failed to *run* the command: {e}{reset}")
                print(f"{red}Maybe the command was weird? Command was: {command}{reset}")

        # INTERACTIVE MODE: Ask first!
        elif mode == "interactive":
            # Ask the user what they wanna do: run, cancel, or copy
            confirm = input(f"{green}Execute this command? (y/yes to run, n/no to cancel, c/copy to copy): {reset}").strip().lower()

            if confirm in ["c", "copy"]:
                # Try to copy to clipboard (this uses 'clip' command on Windows)
                try:
                    # os.system is a simple way to run a command. here we echo the command and pipe it to clip
                    os.system(f"echo {command.strip()} | clip")
                    print(f"{green}\n~ Command copied to clipboard! You can paste it somewhere else.{reset}")
               
                except Exception as e:
                    print(f"{red}Couldn't copy to clipboard automatically. Error: {e}{reset}")
                    print(f"{red}You can still copy it manually: {purple}{command}{reset}")
                continue # go back and ask for the next input

            elif confirm in ["n", "no", "cancel"]:
                # User said no, just abort this command
                print(f"{gold}\n~ Command cancelled. No problemo.{reset}")
                continue # go back and ask for the next input

            elif confirm in ["y", "yes", "run"]:
                # User said YES! Let's run it!
                print(f"{blue}\n~ Okay, running command... fingers crossed!{reset}\n{cyan}--- Command Output Start ---{reset}")
               
                try:
                    # Using subprocess.Popen here is a bit fancier than .run
                    # It lets us capture the output (stdout) and errors (stderr) AS they happen (streaming)
                    # stdout=subprocess.PIPE means we'll catch the normal output
                    # stderr=subprocess.STDOUT means errors will also go to the same place as normal output
                    # text=True makes it easier to read the output as strings
                    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)

                    # Read the output line by line as it comes in
                    output_log = "" # store the output in case we need it
                   
                    for line in process.stdout: # Read line by line
                        print(f"{line}", end="") # print the line immediately, end="" prevents extra newlines
                        output_log += line # add it to our log string

                    process.wait() # wait for the command to fully finish

                    print(f"{cyan}--- Command Output End ---{reset}") # makes it clear when output is done

                    # A little extra check: did the command complain about needing admin rights?
                    if "access is denied" in output_log.lower() or "administrator privileges" in output_log.lower():
                        print(f"\n{red}!! Heads up: Looks like that command might need Administrator powers.{reset}")
                        print(f"{red}!! Try running this script again as an Administrator if it didn't work.{reset}")

                    # Log the command we just ran (if it wasn't cancelled)
                    # 'a' means append mode, adds to the end of the file
                    try:
                    
                        with open("history.log", "a") as log_file:
                            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") # make a nice timestamp
                            log_file.write(f"[{timestamp}] Mode: {mode}, Request: '{user_input}', Ran: '{command}'\n")
                    except Exception as log_e:
                        print(f"{red}Minor issue: Couldn't write to history.log file. Error: {log_e}{reset}")


                except FileNotFoundError:
                    # This happens if the command itself doesnt exist (e.g., typed 'pimg' instead of 'ping')
                     print(f"{red}Error: The command '{command.split()[0]}' wasn't found on your system. Is it installed and in your PATH?{reset}")
                
                except Exception as run_err:
                    # Catch any other problems during execution
                    print(f"{red}Oof, error occurred while *running* the command: {run_err}{reset}")
                    print(f"{red}The command was: {purple}{command}{reset}")
            
            else: # they didnt type y, n, or c...
            
                print(f"{gold}Didn't recognise that option ('{confirm}'). Cancelling command just in case.{reset}")
                continue # go back and ask for next input

        # This part should technically not be reached if mode is 'quick' or 'interactive'
        # but just in case something funky happens with the mode variable...
        else:
        
             print(f"{red}Uh oh, somehow ended up in an unknown mode: '{mode}'. That's weird. Going back to mode selection.{reset}")
             break # Break from inner loop to re-select mode

# The script technically keeps looping forever in the outer `while True`
# until the user explicitly types 'quit' or chooses the Exit option in mode selection.