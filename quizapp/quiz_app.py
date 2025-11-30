import os 
import json
import csv
import random
import tkinter as tk
from tkinter import messagebox, ttk 
# --- New Imports for Image Handling ---
# NOTE: Pillow must be installed for image handling ('pip install Pillow')
from PIL import Image, ImageTk 
# --- END New Imports ---

# --- Pygame Imports for Sound Effects ---
# NOTE: Pygame must be installed for sound to work (pip install pygame)
import pygame
from pygame import mixer
# --- END IMPORTS ---

# Load quiz data from JSON
def load_quiz_data():
    """Loads quiz data from quiz_level.json in the script's directory."""
    try:
        base_dir = os.path.dirname(__file__)
        file_path = os.path.join(base_dir, "quiz_level.json")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    except FileNotFoundError:
        messagebox.showerror("Error", "Quiz data file not found! Please ensure quiz_level.json is in the same folder.")
        return {}
    except json.JSONDecodeError:
        messagebox.showerror("Error", "Invalid JSON format in quiz_level.json.")
        return {}

quiz_levels = load_quiz_data()

# Quiz App Class
class QuizApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🐾 Cat Quiz Adventure 🐾")
        
        # Base dimensions for scaling logic
        self.base_width = 1000
        self.base_height = 600
        
        self.root.geometry(f"{self.base_width}x{self.base_height}")
        self.root.minsize(400, 300) 
        self.root.config(bg="#FFF4E0")

        # Make window responsive
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Game state variables
        self.user_name = ""
        self.q_index = 0
        self.score = 0
        self.selected_level = ""
        self.quiz_data = []
        self.scale = 1.0
        
        # Define volume level (0.3 = 30% volume)
        self.SOUND_VOLUME = 0.3 

        # --- Image Loading (Base objects) ---
        self.base_images = {}
        self.photo_images = {} # Stores resized PhotoImage objects for current scale
        self.current_image_state = 'neutral' # Tracks cat state
        
        # Load all image assets (cat and hearts)
        self.load_base_images()
        # --- END Image Loading ---
        
        # --- Pygame Mixer Initialization and Sound Loading ---
        self.correct_sound = None
        self.wrong_sound = None
        self.click_sound = None 
        try:
            pygame.mixer.init()
            # Load sound files. Files must be named 'correct.wav', 'wrong.wav', 
            # and 'click.wav' (for general interaction) and placed in the script's directory.
            BASE_DIR = os.path.dirname(__file__)

            self.correct_sound = mixer.Sound(os.path.join(BASE_DIR, "correct.wav"))
            self.wrong_sound   = mixer.Sound(os.path.join(BASE_DIR, "wrong.wav"))
            self.click_sound   = mixer.Sound(os.path.join(BASE_DIR, "click.wav"))

            # Apply Volume Change
            self.correct_sound.set_volume(self.SOUND_VOLUME)
            self.wrong_sound.set_volume(self.SOUND_VOLUME)
            self.click_sound.set_volume(self.SOUND_VOLUME) 

            print("Sound mixer initialized and sounds loaded successfully.")
        except pygame.error as e:
            # If Pygame is not installed or sound files are missing, the app continues without sound.
            print("-" * 50)
            print(f"!!! WARNING: SOUND DISABLED !!!")
            print(f"Ensure Pygame is installed ('pip install pygame') and that sound files are present.")
            print(f"Pygame Error: {e}")
            print("-" * 50)
        # --- END SOUND SETUP ---

        # Bind resize event for responsive design
        self.root.bind('<Configure>', self.on_resize)

        self.name_screen()

    def load_base_images(self):
        """Loads the base Image objects using Pillow for cat icons and hearts."""
        # Note: The state keys for cats are updated to include 'cat_' prefix for clarity.
        image_files = {
            'cat_neutral': "cat_neutral.png",
            'cat_sad': "cat_sad.png",
            'cat_excited': "cat_excited.png",
            'heart_full': "heart_full.png",
            'heart_empty': "heart_empty.png",
        }
        
        base_dir = os.path.dirname(__file__)

        for state, filename in image_files.items():
            file_path = os.path.join(base_dir, filename)
            try:
                # Store the base PIL Image object
                self.base_images[state] = Image.open(file_path)
            except FileNotFoundError:
                print(f"WARNING: Image file not found: {filename}. Using fallback text if applicable.")
                self.base_images[state] = None 
            except Exception as e:
                print(f"WARNING: Error loading image {filename}: {e}")
                self.base_images[state] = None

    def get_resized_image(self, state, base_target_size):
        """
        Resizes the base PIL Image for a given state and returns a Tkinter PhotoImage.
        Caches the PhotoImage to prevent garbage collection.
        """
        base_img = self.base_images.get(state)
        if not base_img:
            return None
            
        target_size = int(base_target_size * self.scale)
        if target_size < 1:
            target_size = 1
            
        # Resize using LANCZOS for quality
        resized_img = base_img.resize((target_size, target_size), Image.Resampling.LANCZOS)
        
        # Store and return the PhotoImage (using a unique key for caching)
        key = f"{state}_{target_size}"
        self.photo_images[key] = ImageTk.PhotoImage(resized_img)
        return self.photo_images[key]
        
    def set_cat_icon_image(self, state):
        """Sets the cat icon to the specified state (neutral/sad/excited)."""
        # Map simplified state to full key and set base size
        full_state = f'cat_{state}'
        CAT_BASE_SIZE = 120 
        
        icon_widget = None
        if hasattr(self, 'cat_icon') and self.cat_icon.winfo_exists():
            icon_widget = self.cat_icon
        elif hasattr(self, 'menu_emoji') and self.menu_emoji.winfo_exists():
            icon_widget = self.menu_emoji

        if icon_widget:
            self.current_image_state = state
            img = self.get_resized_image(full_state, CAT_BASE_SIZE)
            if img:
                icon_widget.config(image=img, text='')
                icon_widget.image = img # Prevent garbage collection
            else:
                # Fallback to text if image failed to load
                icon_widget.config(image='', text="❓", font=("Arial", int(80 * self.scale)))

    def play_click_sound(self):
        """Plays the click sound if it is loaded."""
        # This uses pygame.mixer, which is non-blocking (async)
        if self.click_sound:
            self.click_sound.play()

    def on_resize(self, event):
        """Handles responsive scaling of UI elements based on window size."""
        if event.widget == self.root:
            scale_w = event.width / self.base_width
            scale_h = event.height / self.base_height
            
            # Use a slightly buffered minimum scale
            self.scale = min(scale_w, scale_h) * 0.85
            
            # Ensure a minimum readable size
            self.scale = max(self.scale, 0.4)
            
            self.update_ui_scaling()

    def get_font(self, family, size, weight="normal"):
        """Helper to return a scaled font tuple."""
        return (family, int(size * self.scale), weight)

    def update_ui_scaling(self):
        """Updates the font size and element lengths across all screens."""
        
        # 1. MENU SCREEN
        if hasattr(self, 'menu_emoji') and self.menu_emoji.winfo_exists():
            # Update Cat Image (re-size the current one, which should be neutral)
            self.set_cat_icon_image('neutral')

            self.menu_title.config(font=self.get_font("Comic Sans MS", 24, "bold"))
            self.name_entry.config(font=self.get_font("Comic Sans MS", 14))
            self.start_btn.config(font=self.get_font("Comic Sans MS", 14, "bold"))

        # 2. DIFFICULTY SCREEN
        if hasattr(self, 'diff_title') and self.diff_title.winfo_exists():
            self.diff_greeting.config(font=self.get_font("Comic Sans MS", 22, "bold"))
            self.diff_title.config(font=self.get_font("Comic Sans MS", 16))
            for btn in self.diff_buttons:
                btn.config(font=self.get_font("Comic Sans MS", 14, "bold"))
            
            if hasattr(self, 'diff_back_btn') and self.diff_back_btn.winfo_exists():
                self.diff_back_btn.config(font=self.get_font("Comic Sans MS", 12, "bold"))
                # Update Place coordinates
                scaled_x = int(20 * self.scale)
                scaled_y = int(20 * self.scale)
                self.diff_back_btn.place(x=scaled_x, y=scaled_y)


        # 3. QUIZ SCREEN
        if hasattr(self, 'question_label') and self.question_label.winfo_exists():
            # Update Progress Bar length
            new_len = int(600 * self.scale)
            self.progress.config(length=new_len)
            
            # Update Cat Image (re-size the current one based on state)
            self.set_cat_icon_image(self.current_image_state)

            # Update Hearts by regenerating them with resized images
            self.update_hearts()

            # Update Question
            self.question_label.config(
                font=self.get_font("Comic Sans MS", 13),
                wraplength=int(700 * self.scale)
            )

            # Update Options
            for rb in self.option_buttons:
                rb.config(font=self.get_font("Comic Sans MS", 14))

            # Update Controls
            self.feedback_label.config(font=self.get_font("Comic Sans MS", 14, "bold"))
            self.hint_btn.config(font=self.get_font("Comic Sans MS", 12, "bold"))
            self.next_btn.config(font=self.get_font("Comic Sans MS", 14, "bold"))
            
            # Update the Quiz Back Button (Change Level)
            if hasattr(self, 'quiz_back_btn') and self.quiz_back_btn.winfo_exists():
                self.quiz_back_btn.config(
                    font=self.get_font("Comic Sans MS", 10, "bold")
                )
                # Update Place coordinates (lowered Y as requested)
                scaled_x = int(20 * self.scale)
                scaled_y = int(50 * self.scale) # Lowered
                self.quiz_back_btn.place(x=scaled_x, y=scaled_y)


        # 4. GAME OVER SCREEN
        if hasattr(self, 'go_title') and self.go_title.winfo_exists():
            self.go_title.config(font=self.get_font("Comic Sans MS", 30, "bold"))
            self.go_msg.config(font=self.get_font("Comic Sans MS", 18))
            self.go_btn.config(font=self.get_font("Comic Sans MS", 16, "bold"))

        # 5. SCORE SCREEN
        if hasattr(self, 'score_title') and self.score_title.winfo_exists():
            self.score_title.config(font=self.get_font("Comic Sans MS", 24, "bold"))
            self.score_val.config(font=self.get_font("Comic Sans MS", 18))
            self.score_msg.config(font=self.get_font("Comic Sans MS", 16))
            self.score_btn.config(font=self.get_font("Comic Sans MS", 14, "bold"))
            self.retry_btn.config(font=self.get_font("Comic Sans MS", 14, "bold"))

    def save_result_to_csv(self):
        """Appends the current quiz result to a CSV file."""
        if not self.user_name or not self.selected_level or len(self.quiz_data) == 0:
            return

        base_dir = os.path.dirname(__file__)
        file_path = os.path.join(base_dir, "quiz_results.csv")

        file_exists = os.path.isfile(file_path)

        with open(file_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            if not file_exists:
                writer.writerow(["Name", "Difficulty", "Score", "Total Items"])

            writer.writerow([self.user_name, self.selected_level, self.score, len(self.quiz_data)])

    def reset_quiz(self):
        """Resets all quiz state variables."""
        # Preserve user name if known
        self.score = 0
        self.q_index = 0
        self.selected_level = ""
        self.quiz_data = []

    def clear_screen(self):
        """Removes all widgets from the main window."""
        for widget in self.root.winfo_children():
            widget.destroy()

    def update_hearts(self):
        """Renders the heart icons (images) based on current lives."""
        HEART_BASE_SIZE = 25 # Base size for heart image
        
        if not hasattr(self, 'hearts_frame') or not self.hearts_frame.winfo_exists():
            return

        # Clear existing hearts
        for widget in self.hearts_frame.winfo_children():
            widget.destroy()

        # Pre-load the resized images for the current scale
        heart_full_img = self.get_resized_image('heart_full', HEART_BASE_SIZE)
        heart_empty_img = self.get_resized_image('heart_empty', HEART_BASE_SIZE)

        # Fallback text if images are missing
        heart_font = ("Arial", int(17 * self.scale))
        
        for i in range(10):
            is_alive = i < self.lives
            icon = heart_full_img if is_alive else heart_empty_img
            
            if icon:
                # Use image
                heart = tk.Label(self.hearts_frame, image=icon, bg="#FFF4E0")
                heart.image = icon # Prevent garbage collection
            else:
                # Fallback to text
                heart_text = "❤️" if is_alive else "🤍"
                heart = tk.Label(self.hearts_frame, text=heart_text, font=heart_font, bg="#FFF4E0")

            heart.pack(side="left", padx=1, pady=2)
            
    def name_screen(self):
        """Displays the initial screen for entering the user's name."""
        # Only save results if a quiz was attempted (non-empty data)
        if self.quiz_data:
            self.save_result_to_csv()
            
        self.clear_screen()
        # Ensure only name is reset for a fresh start, keep existing self.user_name if returning from a game

        frame = tk.Frame(self.root, bg="#FFF4E0")
        frame.grid(row=0, column=0, sticky="nsew")

        frame.grid_rowconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=0)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        content_frame = tk.Frame(frame, bg="#FFF4E0")
        content_frame.grid(row=1, column=0)

        # Configured to hold the image
        self.menu_emoji = tk.Label(content_frame, bg="#FFF4E0") 
        self.menu_emoji.grid(row=0, column=0, pady=10)
        self.set_cat_icon_image('neutral') # Set initial image

        
        self.menu_title = tk.Label(content_frame, text="Welcome to Cat Quiz Adventure!", font=("Comic Sans MS", 24, "bold"), bg="#FFF4E0")
        self.menu_title.grid(row=1, column=0, pady=10)

        self.name_entry = tk.Entry(content_frame, font=("Comic Sans MS", 14))
        # Pre-fill if a name was previously entered
        if self.user_name:
            self.name_entry.insert(0, self.user_name)
            
        self.name_entry.grid(row=2, column=0, pady=10, ipadx=50)

        self.start_btn = tk.Button(content_frame, text="Start Quiz 🐾", font=("Comic Sans MS", 14, "bold"),
                                     bg="#FF7BA9", fg="white", activebackground="#E86491",
                                     relief="raised", bd=4, width=15, command=self.go_to_difficulty)
        self.start_btn.grid(row=3, column=0, pady=30)
        
        self.update_ui_scaling()

    def go_to_difficulty(self):
        """Displays the screen for selecting quiz difficulty."""
        
        # Check if we are coming from the name screen (entry exists) or back from quiz (entry destroyed)
        if hasattr(self, 'name_entry') and self.name_entry.winfo_exists():
            name = self.name_entry.get().strip()
            if not name:
                messagebox.showwarning("Input Error", "Please enter your name.")
                return
            self.user_name = name
        
        self.play_click_sound() # Play click sound
        self.clear_screen()

        frame = tk.Frame(self.root, bg="#FFF4E0")
        frame.grid(row=0, column=0, sticky="nsew")

        # Configure rows/columns for centering main content
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=0)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        content_frame = tk.Frame(frame, bg="#FFF4E0")
        content_frame.grid(row=1, column=0)

        # Back Button (To Name Screen)
        # Using PLACE instead of grid for reliable sticky positioning
        self.diff_back_btn = tk.Button(frame, text="⬅ Back", font=("Comic Sans MS", 12, "bold"),
                                  bg="#FFAB91", fg="white", bd=0, 
                                  command=lambda: (self.play_click_sound(), self.reset_quiz(), self.name_screen()))
        self.diff_back_btn.place(x=20, y=20)

        self.diff_greeting = tk.Label(content_frame, text=f"Hi {self.user_name}! 👋", font=("Comic Sans MS", 22, "bold"), bg="#FFF4E0")
        self.diff_greeting.grid(row=0, column=0, pady=10)
        
        self.diff_title = tk.Label(content_frame, text="Choose your difficulty level:", font=("Comic Sans MS", 16), bg="#FFF4E0")
        self.diff_title.grid(row=1, column=0, pady=10)

        self.diff_buttons = []
        colors = {"easy": "#8BC34A", "medium": "#FFC107", "hard": "#F44336"}
        for i, level in enumerate(["easy", "medium", "hard"]):
            btn = tk.Button(content_frame, text=level.capitalize(), font=("Comic Sans MS", 14, "bold"),
                             bg=colors[level], fg="white", width=15,
                             command=lambda lvl=level: self.start_quiz(lvl))
            btn.grid(row=i+2, column=0, pady=10)
            self.diff_buttons.append(btn)
            
        self.update_ui_scaling()

    def start_quiz(self, difficulty):
        """Initializes the quiz data for the selected difficulty."""
        self.play_click_sound() # Play click sound
        
        # Reset state variables related to quiz content
        self.selected_level = difficulty.capitalize()
        quiz_data_for_level = quiz_levels.get(difficulty, [])
        
        if not quiz_data_for_level:
            messagebox.showerror("Error", f"No quiz data found for {difficulty} level.")
            return
        
        self.quiz_data = quiz_data_for_level
        
        if not self.quiz_data:
            # Fallback if the data load fails unexpectedly
            self.name_screen()
            return
        
        # Limit to 10 questions for a quick game
        self.quiz_data = self.quiz_data[:10]
        
        # Randomize questions and options
        random.shuffle(self.quiz_data)
        for q in self.quiz_data:
            random.shuffle(q["options"])
        
        self.q_index = 0
        self.score = 0
        self.lives = 10 # 10 lives maximum for a full quiz
        
        self.quiz_screen()

    def quiz_screen(self):
        """Sets up the main quiz question screen."""
        self.clear_screen()
        frame = tk.Frame(self.root, bg="#FFF4E0")
        frame.grid(row=0, column=0, sticky="nsew")

        frame.grid_rowconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=0)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        
        content_frame = tk.Frame(frame, bg="#FFF4E0")
        content_frame.grid(row=1, column=0)

        # Change Difficulty Button - Using PLACE for overlay positioning
        self.quiz_back_btn = tk.Button(
            frame, text="⬅ Change Level", font=("Comic Sans MS", 10, "bold"),
            bg="#FFAB91", fg="white", bd=0,
            command=lambda: (self.play_click_sound(), self.reset_quiz(), self.go_to_difficulty())
        )
        self.quiz_back_btn.place(x=20, y=50) # Initial place, updated in scaling

        # Progress bar
        content_frame.grid_columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(content_frame, length=600, maximum=len(self.quiz_data))
        self.progress.grid(row=0, column=0, pady=(15, 10), padx=10)

        # Cat Icon Frame
        cat_frame = tk.Frame(content_frame, bg="#FFF4E0")
        cat_frame.grid(row=1, column=0, pady=(5, 5))

        # Cat Image Label
        self.cat_icon = tk.Label(cat_frame, bg="#FFF4E0")
        self.cat_icon.pack()

        # Hearts
        self.hearts_frame = tk.Frame(content_frame, bg="#FFF4E0")
        self.hearts_frame.grid(row=2, column=0, pady=(5, 10))

        # Hearts will be updated with images on first display/scaling
        self.update_hearts()

        self.question_label = tk.Label(content_frame, text="", font=("Comic Sans MS", 13), wraplength=700, justify="left", bg="#FFF4E0", anchor="w")
        self.question_label.grid(row=3, column=0, pady=10, padx=60, sticky="ew")

        self.var = tk.StringVar()
        self.var.set(None)

        options_container = tk.Frame(content_frame, bg="#FFF4E0")
        options_container.grid(row=4, column=0, sticky="ew", padx=60, pady=5)
        options_container.grid_columnconfigure(0, weight=1)

        self.option_buttons = []
        self.option_frames = []

        for i in range(4):
            option_frame = tk.Frame(options_container, bg="#FFF4E0", bd=1, relief="solid")
            option_frame.grid(row=i, column=0, sticky="ew", pady=4)
            self.option_frames.append(option_frame)
            
            rb = tk.Radiobutton(option_frame, text="", variable=self.var, value="", font=("Comic Sans MS", 14), bg="#FFF4E0", anchor="w", padx=10, pady=5, command=self.on_option_select)
            rb.pack(fill="x", expand=True)
            self.option_buttons.append(rb)

        self.feedback_label = tk.Label(content_frame, text="", font=("Comic Sans MS", 14, "bold"), bg="#FFF4E0")
        self.feedback_label.grid(row=5, column=0, pady=5)

        self.hint_btn = tk.Button(content_frame, text="Show Hint 💡", font=("Comic Sans MS", 12, "bold"),
                                     bg="#FF9800", fg="white", width=12, command=self.show_hint)
        self.hint_btn.grid(row=6, column=0, pady=(0, 10))

        self.next_btn = tk.Button(content_frame, text="Next 🐾", font=("Comic Sans MS", 14, "bold"),
                                     bg="#FF7BA9", fg="white", width=15, command=self.check_answer)
        self.next_btn.grid(row=7, column=0, pady=(0, 15))

        self.display_question()
        self.update_ui_scaling()

    def display_question(self):
        """Populates the screen with the current question and options."""
        q = self.quiz_data[self.q_index]
        self.question_label.config(text=f"Q{self.q_index+1}: {q['question']}")
        self.var.set(None)
        self.feedback_label.config(text="")
        self.hint_btn.config(state="normal")
        
        # Set to Neutral Cat Image
        self.set_cat_icon_image('neutral')
        
        self.on_option_select(reset=True)

        for i, option in enumerate(q["options"]):
            self.option_buttons[i].config(text=option, value=option, state="normal")

        self.progress['value'] = self.q_index

    def on_option_select(self, reset=False):
        """Highlights the selected radio button and plays a click sound."""
        selected_value = self.var.get()
        
        default_bg = "#FFF4E0"
        selected_bg = "#FFDDC1"

        if not reset and selected_value:
             self.play_click_sound() # Play click sound on selection

        for i, rb in enumerate(self.option_buttons):
            frame = self.option_frames[i]
            if not reset and rb['value'] == selected_value:
                frame.config(bg=selected_bg, relief="groove", bd=2)
                rb.config(bg=selected_bg)
            else:
                frame.config(bg=default_bg, relief="solid", bd=1)
                rb.config(bg=default_bg)

    def show_hint(self):
        """Displays a hint for the current question."""
        self.play_click_sound() # Play click sound
        hint = self.quiz_data[self.q_index].get("hint", "No hint available.")
        messagebox.showinfo("Hint 💡", hint)
        self.hint_btn.config(state="disabled")

    def check_answer(self):
        """Checks the selected answer, updates score/lives, and plays sound."""
        selected = self.var.get()
        if not selected or selected == "None":
            messagebox.showwarning("No answer", "Please select an option before continuing.")
            return

        correct = self.quiz_data[self.q_index]["answer"]
        if selected == correct:
            # Play correct sound (non-blocking)
            if self.correct_sound:
                self.correct_sound.play()

            self.score += 1
            self.feedback_label.config(text="✅ Correct!", fg="green")
            self.set_cat_icon_image('excited') # Set to Excited Cat Image
        else:
            # Play wrong sound (non-blocking)
            if self.wrong_sound:
                self.wrong_sound.play()

            self.feedback_label.config(text=f"❌ Incorrect! Correct: {correct}", fg="red")
            self.set_cat_icon_image('sad') # Set to Sad Cat Image
            self.lose_life()

        # Disable controls after answering
        for rb in self.option_buttons:
            rb.config(state="disabled")
        self.hint_btn.config(state="disabled")
        # Change next button command to the continue action
        self.next_btn.config(text="Continue ➡️", command=self.next_question)

    def lose_life(self):
        """Decrements life count and checks for game over condition."""
        if self.lives > 0:
            self.lives -= 1
            self.update_hearts()

        if self.lives == 0:
            self.game_over()

    def next_question(self):
        """Moves to the next question or the final score screen."""
        self.play_click_sound() # Play click sound when moving to the next question
        self.q_index += 1
        if self.q_index < len(self.quiz_data):
            self.display_question()
            self.next_btn.config(text="Next 🐾", command=self.check_answer)
        else:
            self.show_final_score()

    def retry_same_level(self):
        self.play_click_sound()
        difficulty_key = self.selected_level.lower()
        self.start_quiz(difficulty_key)

    def game_over(self):
        """Displays the game over screen."""
        self.clear_screen()
        frame = tk.Frame(self.root, bg="#FFF4E0")
        frame.grid(row=0, column=0, sticky="nsew")
        
        # Centering
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        content = tk.Frame(frame, bg="#FFF4E0")
        content.grid(row=0, column=0)

        self.go_title = tk.Label(content, text="💔 Game Over 💔", font=("Comic Sans MS", 30, "bold"), bg="#FFF4E0")
        self.go_title.pack(pady=40)
        
        self.go_msg = tk.Label(content, text=f"You ran out of lives, {self.user_name}!", 
              font=("Comic Sans MS", 18), bg="#FFF4E0")
        self.go_msg.pack(pady=10)

        # Updated command to play click sound before switching screen
        self.go_btn = tk.Button(content, text="Return to Menu", 
              font=("Comic Sans MS", 16, "bold"), bg="#FF7BA9", fg="white",
              command=lambda: (self.play_click_sound(), self.reset_quiz(), self.name_screen()))
        self.go_btn.pack(pady=30)
        
        self.update_ui_scaling()

    def show_final_score(self):
        """Displays the final score and quiz result message."""
        self.save_result_to_csv()
        self.clear_screen()
        frame = tk.Frame(self.root, bg="#FFF4E0")
        frame.grid(row=0, column=0, sticky="nsew")

        frame.grid_rowconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=0)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        content_frame = tk.Frame(frame, bg="#FFF4E0")
        content_frame.grid(row=1, column=0, pady=20)

        # Calculate message based on performance
        total_questions = len(self.quiz_data)
        ratio = self.score / total_questions if total_questions > 0 else 0
        
        if ratio == 1:
            msg = "🌟 Excellent! Perfect score!"
        elif ratio >= 0.7:
            msg = "🎉 Great job! You did well!"
        elif ratio >= 0.4:
            msg = "👍 Good effort! Keep practicing!"
        else:
            msg = "💪 Needs improvement. Try again!"

        self.score_title = tk.Label(content_frame, text=f"{self.user_name}, you finished the {self.selected_level} quiz!", font=("Comic Sans MS", 24, "bold"), bg="#FFF4E0")
        self.score_title.grid(row=0, column=0, pady=20)
        
        self.score_val = tk.Label(content_frame, text=f"Your Score: {self.score}/{total_questions}", font=("Comic Sans MS", 18), bg="#FFF4E0")
        self.score_val.grid(row=1, column=0, pady=10)
        
        self.score_msg = tk.Label(content_frame, text=msg, font=("Comic Sans MS", 16), bg="#FFF4E0")
        self.score_msg.grid(row=2, column=0, pady=10)
        button_frame = tk.Frame(content_frame, bg="#FFF4E0")
        button_frame.grid(row=3, column=0, pady=20)

        # Return Button
        self.score_btn = tk.Button(
            button_frame, text="Return ↩️", font=("Comic Sans MS", 14, "bold"),
            bg="#FF7BA9", fg="white", width=15, 
            command=lambda: (self.play_click_sound(), self.reset_quiz(), self.name_screen())
        )
        self.score_btn.pack(side="left", padx=10)
        # -----------------------------

        # Try Again button (LEFT)
        self.retry_btn = tk.Button(
            button_frame, text="Try Again 🔁", font=("Comic Sans MS", 14, "bold"),
            bg="#8BC34A", fg="white", width=15, command=self.retry_same_level
        )
        self.retry_btn.pack(side="left", padx=10)
        
        self.update_ui_scaling()


# Run App
if __name__ == "__main__":
    root = tk.Tk()
    app = QuizApp(root)
    root.mainloop()