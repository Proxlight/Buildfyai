import customtkinter as ctk
import tkinter as tk
from tkinter import scrolledtext, filedialog
import threading
import requests
import json
from pathlib import Path
import os
from pygments import lex
from pygments.lexers import PythonLexer
from pygments.styles import get_style_by_name
from CTkListbox import CTkListbox  # Add this import

class AIGUIBuilder(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("✨ Buildfy AI")  # Added sparkle emoji
        self.geometry("1380x700")
        self.resizable(False,False)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Notion-inspired color palette
        self.colors = {

        'bg_primary': '#1E1F22',      # Deep charcoal (cleaner than pure black)
        'bg_secondary': '#2A2B2F',    # Smooth dark gray for contrast
        'accent': '#7F5AF0',          # Soft vibrant violet (modern and eye-catching)
        'text_primary': '#E4E4E7',    # Light gray-white (less harsh than pure white)
        'text_secondary': '#A1A1AA',  # Muted gray (friendly on the eyes)
        'success': '#3DDC84',         # Fresh green (modern success color)
        'error': '#FF6B6B',           # Soft coral red (gentler error tone)
        'border': '#3A3B3F'           # Subtle border with a cool tone

        }
        
        self.configure(fg_color=self.colors['bg_primary'])
        
        self.prompt_history = []
        self.code_versions = []
        self.current_code = ""
        
        # Licensing and usage
        self.settings_file = Path(os.path.expanduser('~')) / '.aigui_settings.json'
        settings = self._load_api_settings()
        self.api_key = settings.get('api_key', '')
        self.license_key = settings.get('license_key', '')
        self.generation_count = settings.get('generation_count', 0)
        self.generation_month = settings.get('generation_month', '')
        self.max_generations = 3
        self.full_license = "Buy it Now"
        self.gumroad_url = "https://proxlightapps.gumroad.com/l/BuildfyAI"  # Replace with your actual Gumroad page
        
        self._build_layout()
        self._render_initial_ui()
        self._update_export_button_state()

    def _build_layout(self):
        # Configure grid layout
        self.grid_columnconfigure(0, weight=1, uniform="a")
        self.grid_columnconfigure(1, weight=2, uniform="a")
        self.grid_rowconfigure(0, weight=1)

        # Left panel: Chat, Code Editor, Controls
        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.left_frame.grid_rowconfigure(2, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)

        # Chat history with improved styling
        self.chat_frame = ctk.CTkFrame(self.left_frame)
        self.chat_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        self.chat_history = scrolledtext.ScrolledText(
            self.chat_frame,
            height=10,
            state='disabled',
            wrap='word',
            font=("Segoe UI", 11)
        )
        self.chat_history.pack(expand=True, fill="both", padx=5, pady=5)

        # Prompt input area
        self.input_frame = ctk.CTkFrame(self.left_frame)
        self.input_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        self.prompt_entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Describe your UI in natural language...",
            height=35,
            font=("Segoe UI", 12)
        )
        self.prompt_entry.pack(side="left", expand=True, fill="x", padx=(5, 5))
        self.prompt_entry.bind('<Return>', self._on_prompt_submit)

        # Add context toggle in input frame
        self.context_var = tk.BooleanVar(value=True)
        self.context_toggle = ctk.CTkSwitch(
            self.input_frame,
            text="Use Current Context",
            variable=self.context_var,
            width=150,
            font=("Segoe UI", 12),
            progress_color=self.colors['accent']
        )
        self.context_toggle.pack(side="right", padx=10)

        self.submit_btn = ctk.CTkButton(
            self.input_frame,
            text="✨",  # Updated button text with emoji
            width=120,  # Increased width to fit text
            height=35,
            command=self._on_prompt_submit,
            font=("Segoe UI", 13),
            fg_color=self.colors['accent'],
            hover_color=self.colors['text_secondary']
        )
        self.submit_btn.pack(side="right", padx=5)

        # Code editor with syntax highlighting
        self.code_frame = ctk.CTkFrame(self.left_frame)
        self.code_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        
        # Line numbers text widget
        self.line_numbers = tk.Text(
            self.code_frame,
            width=4,
            padx=5,
            pady=5,
            takefocus=0,
            border=0,
            background='#2d2d2d',
            foreground='#6e7681',
            font=("Consolas", 12),
            state='disabled'
        )
        self.line_numbers.pack(side="left", fill="y")
        
        # Code editor with syntax highlighting
        self.code_editor = scrolledtext.ScrolledText(
            self.code_frame,
            height=20,
            wrap='none',
            font=("Consolas", 12),
            bg='#1e1e1e',
            fg='#d4d4d4',
            insertbackground='white',
            tabs=4
        )
        self.code_editor.pack(side="left", expand=True, fill="both", padx=(0, 5), pady=5)
        self.code_editor.bind('<KeyRelease>', self._on_code_edit)
        self.code_editor.bind('<Key>', self._update_line_numbers)
        self.code_editor.bind('<MouseWheel>', self._sync_line_numbers)

        # Control buttons
        self.control_frame = ctk.CTkFrame(self.left_frame)
        self.control_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        # Trial Button
        self.trial_btn = ctk.CTkButton(
            self.control_frame,
            text="Trial Mode",
            command=self._activate_trial_mode,
            fg_color="#3DDC84",
            hover_color="#1E1F22",
            text_color="#181A1B"
        )
        self.trial_btn.pack(side="left", expand=True, padx=5)
        
        self.settings_btn = ctk.CTkButton(
            self.control_frame,
            text="API Settings",
            command=self._show_settings
        )
        self.settings_btn.pack(side="left", expand=True, padx=5)

        # Add Buy Full Version button
        self.buy_btn = ctk.CTkButton(
            self.control_frame,
            text="Buy Full Version",
            command=self._on_buy_click,
            fg_color="#FFD700",
            hover_color="#B8860B",
            text_color="#181A1B"
        )
        self.buy_btn.pack(side="left", expand=True, padx=5)

        # Right panel: Preview
        self.canvas_frame = ctk.CTkFrame(self)
        self.canvas_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)
        
        # Add a label to indicate this is the preview area
        self.preview_label = ctk.CTkLabel(
            self.canvas_frame,
            text="UI Preview",
            font=("Segoe UI", 14, "bold")
        )
        self.preview_label.pack(pady=(10, 0))

    def _render_initial_ui(self):
        welcome_message = "Welcome! Enter a description of your desired UI and I'll generate it using Gemini AI."
        self._update_chat("AI", welcome_message)
        initial_code = self._get_default_code()
        self._update_code_editor(initial_code)
        self._render_canvas(initial_code)

    def _get_default_code(self):
        return '''import customtkinter as ctk

class GeneratedUI(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.welcome_label = ctk.CTkLabel(
            self,
            text="Welcome to AI GUI Builder!",
            font=("Segoe UI", 20, "bold")
        )
        self.welcome_label.pack(pady=20)
        
        self.desc_label = ctk.CTkLabel(
            self,
            text="Enter a prompt to generate your UI with Gemini AI",
            font=("Segoe UI", 14)
        )
        self.desc_label.pack(pady=10)
'''

    def _on_prompt_submit(self, event=None):
        # Licensing check
        if not self._has_full_license():
            self._check_monthly_reset()
            if self.generation_count >= self.max_generations:
                self._update_chat("AI", "You have reached the free limit of 3 generations this month. Please purchase the full version to unlock unlimited generations.")
                return
        prompt = self.prompt_entry.get().strip()
        if not prompt:
            return
        
        # Include current code as context for the AI based on toggle
        full_prompt = prompt
        if self.current_code and self.current_code.strip() and self.context_var.get():
            self._update_chat("You", f"{prompt} (with current code context)")
            # Add the current code as context to the prompt
            full_prompt = f"CURRENT CODE:\n{self.current_code}\n\nUSER REQUEST: {prompt}\n\nModify the current code according to the request while preserving the overall structure and functionality."
        else:
            self._update_chat("You", prompt)
        
        self.prompt_history.append(prompt)
        self.submit_btn.configure(state="disabled", text="Generating...")
        # Show pending message
        self._show_pending_message()
        threading.Thread(target=self._process_and_render, args=(full_prompt,), daemon=True).start()
        self.prompt_entry.delete(0, tk.END)
        if not self._has_full_license():
            self.generation_count += 1
            self._save_api_settings()
            self._update_export_button_state()

    def _show_pending_message(self):
        """Add a pending message to the chat history to indicate processing"""
        self._update_chat("AI", "Thinking... (generating UI)")

    def _process_and_render(self, prompt):
        try:
            code = self._process_prompt(prompt)
            self.code_versions.append(code)
            self.current_code = code
            self.after(0, lambda: self._update_code_editor(code))
            self.after(0, lambda: self._render_canvas(code))
            # Replace the "Thinking..." message with success message
            self._update_chat("AI", "UI generated successfully!")
        except Exception as e:
            self._update_chat("AI", f"Error generating UI: {str(e)}")
        finally:
            self.submit_btn.configure(state="normal", text="✨")

    def _load_api_settings(self):
        if self.settings_file.exists():
            try:
                with open(self.settings_file) as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _check_monthly_reset(self):
        import datetime
        now_month = datetime.datetime.now().strftime("%Y-%m")
        if self.generation_month != now_month:
            self.generation_count = 0
            self.generation_month = now_month
            self._save_api_settings()
    
    def _save_api_settings(self):
        import datetime
        now_month = datetime.datetime.now().strftime("%Y-%m")
        with open(self.settings_file, 'w') as f:
            json.dump({
                'api_key': self.api_key,
                'license_key': self.license_key,
                'generation_count': self.generation_count,
                'generation_month': now_month if self.generation_month == '' else self.generation_month
            }, f)
    
    def _show_settings(self):
        settings_window = ctk.CTkToplevel(self)
        settings_window.title("Gemini API Settings")
        settings_window.geometry("500x250")
        settings_window.transient(self)
        settings_window.grab_set()
        
        # API Key input only
        api_key_label = ctk.CTkLabel(
            settings_window, 
            text="Gemini API Key:",
            font=("Segoe UI", 14, "bold")
        )
        api_key_label.pack(pady=(20,5))
        
        api_key_entry = ctk.CTkEntry(settings_window, width=400, show="*")
        api_key_entry.insert(0, self.api_key)
        api_key_entry.pack(pady=5)
        
        instruction_label = ctk.CTkLabel(
            settings_window,
            text="Get your API key from: https://ai.google.dev/",
            font=("Segoe UI", 12)
        )
        instruction_label.pack(pady=10)
        
        def save_settings():
            self.api_key = api_key_entry.get()
            self._save_api_settings()
            settings_window.destroy()
            self._update_export_button_state()
            self._update_chat("AI", "Settings saved.")
        
        save_btn = ctk.CTkButton(
            settings_window,
            text="Save",
            command=save_settings,
            width=200,
            height=40
        )
        save_btn.pack(pady=20)
    
    def _has_full_license(self):
        return self.license_key.strip() == self.full_license
    
    def _update_export_button_state(self):
        pass
    
    def _open_gumroad(self):
        import webbrowser
        webbrowser.open(self.gumroad_url)
    
    def _process_prompt(self, prompt):
        if not self.api_key:
            self._update_chat("AI", "Please set your Gemini API key in settings first!")
            return self._get_default_code()
        
        try:
            # Gemini API endpoint
            api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"
            
            # Add API key as a query parameter
            api_url = f"{api_url}?key={self.api_key}"
            
            # Check if this is a modification request (contains current code)
            is_modification = "CURRENT CODE:" in prompt
            
            # Prepare the prompt with specific instructions
            if is_modification:
                system_prompt = """You are a specialized UI code modifier for customtkinter Python applications.
Modify the provided code based on the user's request. The code must:
1. Maintain the existing structure and functionality unless explicitly asked to change
2. Use customtkinter widgets (ctk.CTkLabel, ctk.CTkButton, ctk.CTkEntry, etc.)
3. Have proper layout management (pack, grid, or place)
4. Include appropriate styling (fonts, colors, padding)
5. MUST follow the class structure: class GeneratedUI(ctk.CTkFrame)
6. Only output Python code without any explanations or markdown formatting"""
            else:
                system_prompt = """You are a specialized UI code generator for customtkinter Python applications. 
Generate clean, well-structured Python code for a GUI based on the user's description.
The code must:
1. Use customtkinter widgets (ctk.CTkLabel, ctk.CTkButton, ctk.CTkEntry, etc.)
2. Have proper layout management (pack, grid, or place)
3. Include appropriate styling (fonts, colors, padding)
4. Implement basic functionality where relevant
5. MUST follow this class structure: class GeneratedUI(ctk.CTkFrame)
6. Include proper __init__ method with self and master parameters
7. Only output Python code without any explanations or markdown formatting

Here's an example of the expected code format:
```python
import customtkinter as ctk

class GeneratedUI(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        # UI components go here
```"""

            response = requests.post(
                api_url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {"text": system_prompt},
                                {"text": f"{'Modify the code according to this request' if is_modification else 'Create a customtkinter GUI with these requirements'}: {prompt}"}
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.2,
                        "topK": 32,
                        "topP": 0.95,
                        "maxOutputTokens": 2048,
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                # Extract the generated code
                generated_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                
                # Clean up the code by removing code blocks if present
                code = generated_text.replace("```python", "").replace("```", "").strip()
                
                # Validate that it contains the required class definition
                if "class GeneratedUI(ctk.CTkFrame)" not in code:
                    self._update_chat("AI", "Error: The generated code doesn't contain the required class structure. Trying to fix it...")
                    # Add the basic class structure if it's missing
                    if "import customtkinter as ctk" not in code:
                        code = "import customtkinter as ctk\n\n" + code
                    
                    if "class GeneratedUI" not in code:
                        code = code + "\n\nclass GeneratedUI(ctk.CTkFrame):\n    def __init__(self, master):\n        super().__init__(master)\n        # Auto-generated UI"
                
                return code
            else:
                error_msg = f"API Error: {response.status_code}"
                try:
                    error_details = response.json().get("error", {}).get("message", "Unknown error")
                    error_msg += f" - {error_details}"
                except:
                    pass
                
                self._update_chat("AI", error_msg)
                return self._get_default_code()
        
        except Exception as e:
            self._update_chat("AI", f"Error calling Gemini API: {str(e)}")
            return self._get_default_code()

    def _update_chat(self, sender, message):
        self.chat_history.configure(state='normal')
        
        # If it's a new AI message and the last message was from AI (thinking message)
        if sender == "AI" and self.chat_history.get("end-2l linestart", "end-1l lineend").startswith("AI: Thinking..."):
            # Delete the last "thinking" message
            self.chat_history.delete("end-3l linestart", "end-1l lineend")
            self.chat_history.insert(tk.END, f"{sender}: {message}\n\n")
        else:
            # Normal message insertion
            self.chat_history.insert(tk.END, f"{sender}: {message}\n\n")
            
        self.chat_history.configure(state='disabled')
        self.chat_history.see(tk.END)

    def _update_line_numbers(self, event=None):
        """Update the line numbers in the code editor"""
        lines = self.code_editor.get("1.0", "end-1c").split("\n")
        line_numbers_text = "\n".join(str(i+1) for i in range(len(lines)))
        self.line_numbers.configure(state='normal')
        self.line_numbers.delete("1.0", "end")
        self.line_numbers.insert("1.0", line_numbers_text)
        self.line_numbers.configure(state='disabled')
        self._sync_line_numbers()

    def _sync_line_numbers(self, event=None):
        """Synchronize line numbers with code editor scrolling"""
        first, _ = self.code_editor.yview()
        self.line_numbers.yview_moveto(first)

    def _update_code_editor(self, code):
        """Update the code editor with new code"""
        self.code_editor.configure(state='normal')
        self.code_editor.delete("1.0", "end")
        self.code_editor.insert("1.0", code)
        self.code_editor.configure(state='normal')
        self._update_line_numbers()
        self._apply_syntax_highlighting()
    
    def _on_code_edit(self, event=None):
        """Handle code editing events"""
        self.current_code = self.code_editor.get("1.0", "end-1c")
        self._update_line_numbers()
        self._apply_syntax_highlighting()
        # Optionally re-render the canvas with the edited code
        self._render_canvas(self.current_code)
    
    def _on_export_click(self):
        pass
    
    def _prepare_complete_app_code(self, ui_code):
        return ui_code
    
    def _clean_code_for_export(self, code):
        return code
    
    def _export_code(self):
        pass

    def _activate_trial_mode(self):
        self.license_key = "TRIAL"
        self.max_generations = 3
        self._save_api_settings()
        self._update_chat("AI", "Trial mode activated! You have 3 free generations this month.")
        self._update_export_button_state()

    def _render_canvas(self, code):
        # Clear previous content
        for widget in self.canvas_frame.winfo_children():
            if widget != self.preview_label:
                widget.destroy()
            
        try:
            # Create a clean environment with necessary imports
            local_env = {
                'ctk': ctk,
                'tk': tk,
                'CTkFrame': ctk.CTkFrame,
                'CTkLabel': ctk.CTkLabel,
                'CTkButton': ctk.CTkButton,
                'CTkEntry': ctk.CTkEntry,
                'CTkCheckBox': ctk.CTkCheckBox,
                'CTkSwitch': ctk.CTkSwitch,
                'CTkOptionMenu': ctk.CTkOptionMenu,
                'CTkRadioButton': ctk.CTkRadioButton,
                'CTkSlider': ctk.CTkSlider,
                'CTkProgressBar': ctk.CTkProgressBar,
                'CTkTextbox': ctk.CTkTextbox,
                'CTkTabview': ctk.CTkTabview,
                'CTkListbox': CTkListbox,
                'StringVar': tk.StringVar,
                'IntVar': tk.IntVar,
                'BooleanVar': tk.BooleanVar,
                'DoubleVar': tk.DoubleVar,
                # Add direct access to widgets
                'Frame': tk.Frame,
                'Label': tk.Label,
                'Button': tk.Button,
                'Entry': tk.Entry,
                'Text': tk.Text,
                'Scrollbar': tk.Scrollbar,
                # Add the module itself
                'customtkinter': ctk,
                # Add self reference for class methods
                'self': None
            }
            
            try:
                # First pass: compile to check for syntax errors
                compiled_code = compile(code, '<string>', 'exec')
                
                # Second pass: execute in the prepared environment
                exec(compiled_code, local_env, local_env)
                
                if 'GeneratedUI' in local_env:
                    # Create a wrapper frame with proper styling
                    wrapper_frame = ctk.CTkFrame(
                        self.canvas_frame,
                        fg_color=self.colors['bg_secondary']
                    )
                    wrapper_frame.pack(expand=True, fill='both', padx=20, pady=(30, 20))
                    
                    # Instantiate the generated UI class with proper error handling
                    try:
                        ui_class = local_env['GeneratedUI']
                        ui = ui_class(wrapper_frame)
                        ui.pack(expand=True, fill='both', padx=10, pady=10)
                    except Exception as ui_error:
                        raise Exception(f"Error instantiating UI: {str(ui_error)}")
                else:
                    raise Exception("No GeneratedUI class found in the code")
                    
            except SyntaxError as se:
                raise Exception(f"Syntax error in generated code: {str(se)}")
                
        except Exception as e:
            error_label = ctk.CTkLabel(
                self.canvas_frame,
                text=f"Error rendering UI: {str(e)}",
                text_color=self.colors['error'],
                wraplength=400,
                font=("Segoe UI", 14)
            )
            error_label.pack(expand=True, padx=20, pady=20)
            self._update_chat("AI", f"Preview error: {str(e)}")

    def _apply_syntax_highlighting(self, event=None):
        """Apply syntax highlighting to the code editor"""
        code = self.code_editor.get("1.0", "end-1c")
        self.code_editor.tag_remove("token", "1.0", "end")
        
        # Dracula color palette for syntax highlighting
        highlight_colors = {
            'Keyword': '#ff79c6',   # pink
            'String': '#f1fa8c',    # yellow
            'Number': '#bd93f9',    # purple
            'Comment': '#6272a4',   # comment blue
            'Function': '#50fa7b',  # green
            'Class': '#8be9fd',     # cyan
            'Builtin': '#8be9fd',   # cyan
            'Operator': '#ff79c6',  # pink
        }
        
        # Configure tags for different token types
        for token_type, color in highlight_colors.items():
            self.code_editor.tag_configure(token_type, foreground=color)
        
        # Use Pygments to tokenize the code
        for token, content in lex(code, PythonLexer()):
            start_index = self.code_editor.index("insert")
            end_index = f"{start_index}+{len(content)}c"
            token_name = token.__class__.__name__
            if token_name in highlight_colors:
                self.code_editor.insert("insert", content, token_name)
            else:
                self.code_editor.insert("insert", content)
    
        # Apply syntax highlighting
        try:
            for token, content in lex(code, PythonLexer()):
                token_type = str(token[0])
                if token_type in highlight_colors:
                    start = self.code_editor.search(content, "1.0", tk.END, exact=True)
                    if start:
                        end = f"{start}+{len(content)}c"
                        self.code_editor.tag_add(token_type, start, end)
        except Exception:
            pass  # Ignore highlighting errors

    def _update_code_editor(self, code):
        self.code_editor.delete("1.0", tk.END)
        self.code_editor.insert(tk.END, code)
        self._apply_syntax_highlighting()
        self._update_line_numbers()

    def _on_code_edit(self, event=None):
        code = self.code_editor.get("1.0", tk.END)
        self.current_code = code
        self._apply_syntax_highlighting()
        self._update_line_numbers()
        self._render_canvas(code)

    def _render_canvas(self, code):
        # Clear previous content
        for widget in self.canvas_frame.winfo_children():
            if widget != self.preview_label:
                widget.destroy()
            
        try:
            # Create a clean environment with necessary imports
            local_env = {
                'ctk': ctk,
                'tk': tk,
                'CTkFrame': ctk.CTkFrame,
                'CTkLabel': ctk.CTkLabel,
                'CTkButton': ctk.CTkButton,
                'CTkEntry': ctk.CTkEntry,
                'CTkCheckBox': ctk.CTkCheckBox,
                'CTkSwitch': ctk.CTkSwitch,
                'CTkOptionMenu': ctk.CTkOptionMenu,
                'CTkRadioButton': ctk.CTkRadioButton,
                'CTkSlider': ctk.CTkSlider,
                'CTkProgressBar': ctk.CTkProgressBar,
                'CTkTextbox': ctk.CTkTextbox,
                'CTkTabview': ctk.CTkTabview,
                'CTkListbox': CTkListbox,
                'StringVar': tk.StringVar,
                'IntVar': tk.IntVar,
                'BooleanVar': tk.BooleanVar,
                'DoubleVar': tk.DoubleVar,
                # Add direct access to widgets
                'Frame': tk.Frame,
                'Label': tk.Label,
                'Button': tk.Button,
                'Entry': tk.Entry,
                'Text': tk.Text,
                'Scrollbar': tk.Scrollbar,
                # Add the module itself
                'customtkinter': ctk,
                # Add self reference for class methods
                'self': None
            }
            
            try:
                # First pass: compile to check for syntax errors
                compiled_code = compile(code, '<string>', 'exec')
                
                # Second pass: execute in the prepared environment
                exec(compiled_code, local_env, local_env)
                
                if 'GeneratedUI' in local_env:
                    # Create a wrapper frame with proper styling
                    wrapper_frame = ctk.CTkFrame(
                        self.canvas_frame,
                        fg_color=self.colors['bg_secondary']
                    )
                    wrapper_frame.pack(expand=True, fill='both', padx=20, pady=(30, 20))
                    
                    # Instantiate the generated UI class with proper error handling
                    try:
                        ui_class = local_env['GeneratedUI']
                        ui = ui_class(wrapper_frame)
                        ui.pack(expand=True, fill='both', padx=10, pady=10)
                    except Exception as ui_error:
                        raise Exception(f"Error instantiating UI: {str(ui_error)}")
                else:
                    raise Exception("No GeneratedUI class found in the code")
                    
            except SyntaxError as se:
                raise Exception(f"Syntax error in generated code: {str(se)}")
                
        except Exception as e:
            error_label = ctk.CTkLabel(
                self.canvas_frame,
                text=f"Error rendering UI: {str(e)}",
                text_color=self.colors['error'],
                wraplength=400,
                font=("Segoe UI", 14)
            )
            error_label.pack(expand=True, padx=20, pady=20)
            self._update_chat("AI", f"Preview error: {str(e)}")

    def _on_buy_click(self):
        """Open the Gumroad purchase page"""
        self._update_chat("AI", "Opening purchase page...")
        self._open_gumroad()
    
    def _show_license_prompt(self, message):
        prompt = ctk.CTkToplevel(self)
        prompt.title("Unlock Full Version")
        prompt.geometry("400x250")
        prompt.transient(self)
        prompt.grab_set()
        ctk.CTkLabel(prompt, text=message, font=("Segoe UI", 13)).pack(pady=20)
        ctk.CTkLabel(prompt, text="Enter License Key:", font=("Segoe UI", 12)).pack(pady=(10, 5))
        entry = ctk.CTkEntry(prompt, width=300, show="*")
        entry.pack(pady=5)
        def activate():
            self.license_key = entry.get()
            self._save_api_settings()
            self._update_export_button_state()
            if self._has_full_license():
                self._update_chat("AI", "Full license activated! Unlimited generations unlocked.")
                prompt.destroy()
            else:
                self._update_chat("AI", "Invalid license key. Please try again or purchase a valid license.")
        ctk.CTkButton(prompt, text="Activate", command=activate, width=120).pack(pady=10)
        ctk.CTkButton(prompt, text="Buy Full Version", command=self._open_gumroad, fg_color="#FFD700", text_color="#181A1B").pack(pady=5)
        ctk.CTkButton(prompt, text="Cancel", command=prompt.destroy).pack(pady=5)

if __name__ == "__main__":
    app = AIGUIBuilder()
    app.mainloop()
