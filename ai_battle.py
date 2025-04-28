import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox, simpledialog
import requests
import threading
import time
import sys
import datetime
from tenacity import retry, stop_after_attempt, wait_exponential

class AIBattleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Grok vs. ChatGPT Battle")
        self.root.geometry("900x700")
        self.root.resizable(True, True)

        # API Configuration
        self.XAI_API_KEY = ""
        self.OPENAI_API_KEY = ""
        self.XAI_API_ENDPOINT = "https://api.x.ai/v1/chat/completions"
        self.OPENAI_API_ENDPOINT = "https://api.openai.com/v1/chat/completions"
        self.XAI_MODELS = ["grok-beta", "grok-3-mini-beta"]  # Update as per xAI docs
        self.OPENAI_MODELS = ["gpt-4", "gpt-3.5-turbo"]

        self.battle_log = ""
        self.total_rounds = 3
        self.stop_battle = False

        self.ask_for_api_keys()
        self.create_widgets()

    def ask_for_api_keys(self):
        self.XAI_API_KEY = simpledialog.askstring("API Key Required", "Enter your xAI (Grok) API Key:", show="*")
        self.OPENAI_API_KEY = simpledialog.askstring("API Key Required", "Enter your OpenAI API Key:", show="*")
        if not self.XAI_API_KEY or not self.OPENAI_API_KEY:
            messagebox.showerror("Missing API Keys", "Both API keys are required to run.")
            sys.exit(1)
        # Validate keys
        if not self.validate_api_keys():
            messagebox.showerror("Invalid API Keys", "One or both API keys are invalid. Please restart and try again.")
            sys.exit(1)

    def validate_api_keys(self):
        try:
            self.call_xai_api("Test", validate=True)
            self.call_openai_api("Test", validate=True)
            return True
        except Exception:
            return False

    def create_widgets(self):
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Response Frame
        self.response_frame = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.response_frame.pack(fill=tk.BOTH, expand=True)

        # Grok Frame
        self.grok_frame = tk.Frame(self.response_frame)
        self.response_frame.add(self.grok_frame, weight=1)
        tk.Label(self.grok_frame, text="Grok's Response", font=("Arial", 12, "bold")).pack(anchor="w", pady=5)
        self.grok_text = scrolledtext.ScrolledText(self.grok_frame, wrap=tk.WORD)
        self.grok_text.pack(fill=tk.BOTH, expand=True)
        self.grok_text.insert(tk.END, "Waiting for query...\n")
        self.grok_text.config(state='disabled')
        self.grok_text.tag_config("error", foreground="red")
        self.grok_text.tag_config("followup", foreground="blue")

        # ChatGPT Frame
        self.chatgpt_frame = tk.Frame(self.response_frame)
        self.response_frame.add(self.chatgpt_frame, weight=1)
        tk.Label(self.chatgpt_frame, text="ChatGPT's Response", font=("Arial", 12, "bold")).pack(anchor="w", pady=5)
        self.chatgpt_text = scrolledtext.ScrolledText(self.chatgpt_frame, wrap=tk.WORD)
        self.chatgpt_text.pack(fill=tk.BOTH, expand=True)
        self.chatgpt_text.insert(tk.END, "Waiting for query...\n")
        self.chatgpt_text.config(state='disabled')
        self.chatgpt_text.tag_config("error", foreground="red")
        self.chatgpt_text.tag_config("followup", foreground="blue")

        # Input Frame
        self.input_frame = tk.Frame(self.main_frame)
        self.input_frame.pack(fill=tk.X, pady=10)

        tk.Label(self.input_frame, text="Your Query:").pack(side=tk.LEFT, padx=5)
        self.query_entry = tk.Entry(self.input_frame, width=50)
        self.query_entry.pack(side=tk.LEFT, padx=5)
        self.query_entry.bind("<Return>", lambda event: self.submit_query())

        self.battle_mode = tk.BooleanVar()
        tk.Checkbutton(self.input_frame, text="Battle Mode", variable=self.battle_mode).pack(side=tk.LEFT, padx=5)

        tk.Label(self.input_frame, text="Rounds:").pack(side=tk.LEFT, padx=5)
        self.rounds_entry = tk.Spinbox(self.input_frame, from_=1, to_=10, width=5)
        self.rounds_entry.pack(side=tk.LEFT, padx=5)

        tk.Label(self.input_frame, text="Grok Model:").pack(side=tk.LEFT, padx=5)
        self.xai_model = tk.StringVar(value=self.XAI_MODELS[0])
        tk.OptionMenu(self.input_frame, self.xai_model, *self.XAI_MODELS).pack(side=tk.LEFT, padx=5)

        tk.Label(self.input_frame, text="OpenAI Model:").pack(side=tk.LEFT, padx=5)
        self.openai_model = tk.StringVar(value=self.OPENAI_MODELS[0])
        tk.OptionMenu(self.input_frame, self.openai_model, *self.OPENAI_MODELS).pack(side=tk.LEFT, padx=5)

        self.auto_save = tk.BooleanVar()
        tk.Checkbutton(self.input_frame, text="Auto-Save", variable=self.auto_save).pack(side=tk.LEFT, padx=5)

        self.submit_button = tk.Button(self.input_frame, text="Send", command=self.submit_query)
        self.submit_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = tk.Button(self.input_frame, text="Stop", command=self.stop_battle_thread, state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = tk.Button(self.input_frame, text="Clear", command=self.clear_all)
        self.clear_button.pack(side=tk.LEFT, padx=5)

        self.save_button = tk.Button(self.input_frame, text="Save Battle", command=self.save_battle)
        self.save_button.pack(side=tk.LEFT, padx=5)

        # Progress Bar
        self.progress_frame = tk.Frame(self.main_frame)
        self.progress_frame.pack(fill=tk.X, pady=5)
        self.progress_label = tk.Label(self.progress_frame, text="Progress: Waiting...")
        self.progress_label.pack(side=tk.LEFT, padx=5)
        self.progress_bar = ttk.Progressbar(self.progress_frame, length=400, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, padx=5)

    def submit_query(self):
        query = self.query_entry.get().strip()
        if not query:
            return

        self.stop_battle = False
        self.clear_text_widgets()
        self.battle_log = f"User Query: {query}\n\n"
        self.progress_bar["value"] = 0
        self.progress_label.config(text="Progress: Starting...")

        self.update_response(self.grok_text, "Loading...\n")
        self.update_response(self.chatgpt_text, "Loading...\n")

        self.submit_button.config(state='disabled')
        self.clear_button.config(state='disabled')
        self.save_button.config(state='disabled')
        self.stop_button.config(state='normal')

        threading.Thread(target=self.process_query, args=(query,), daemon=True).start()

    def process_query(self, query):
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.battle_log += f"[{timestamp}] Initial Responses\n"

            self.update_progress(0.25)
            grok_response = self.call_xai_api(query)
            self.append_response(self.grok_text, f"[{timestamp}] Grok: {grok_response}\n")
            self.battle_log += f"[{timestamp}] Grok: {grok_response}\n\n"

            self.update_progress(0.5)
            chatgpt_response = self.call_openai_api(query)
            self.append_response(self.chatgpt_text, f"[{timestamp}] ChatGPT: {chatgpt_response}\n")
            self.battle_log += f"[{timestamp}] ChatGPT: {chatgpt_response}\n\n"

            if self.battle_mode.get() and not self.stop_battle:
                self.total_rounds = int(self.rounds_entry.get())
                for i in range(1, self.total_rounds + 1):
                    if self.stop_battle:
                        self.append_response(self.grok_text, "Battle stopped by user.\n", error=True)
                        self.append_response(self.chatgpt_text, "Battle stopped by user.\n", error=True)
                        self.battle_log += "Battle stopped by user.\n\n"
                        break

                    self.update_progress(0.5 + (i / (self.total_rounds + 1)) * 0.5)
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    grok_followup = self.call_xai_api(f"Respond to this: {chatgpt_response}")
                    self.append_response(self.grok_text, f"[{timestamp}] Round {i} Grok: {grok_followup}\n", tag="followup")
                    self.battle_log += f"[{timestamp}] Round {i} Grok: {grok_followup}\n\n"

                    chatgpt_followup = self.call_openai_api(f"Respond to this: {grok_followup}")
                    self.append_response(self.chatgpt_text, f"[{timestamp}] Round {i} ChatGPT: {chatgpt_followup}\n", tag="followup")
                    self.battle_log += f"[{timestamp}] Round {i} ChatGPT: {chatgpt_followup}\n\n"

                    chatgpt_response = chatgpt_followup
                    time.sleep(0.5)

            self.update_progress(1.0, final=True)
            if self.auto_save.get():
                self.auto_save_battle()

        except requests.exceptions.HTTPError as e:
            error_msg = {
                401: "Invalid API key. Please re-enter keys.",
                429: "Rate limit exceeded. Try again later.",
                500: "Server error. Please try again later."
            }.get(e.response.status_code, f"HTTP error: {str(e)}")
            self.append_response(self.grok_text, f"Error: {error_msg}\n", error=True)
            self.append_response(self.chatgpt_text, f"Error: {error_msg}\n", error=True)
            self.battle_log += f"Error: {error_msg}\n\n"
        except Exception as e:
            self.append_response(self.grok_text, f"Error: {str(e)}\n", error=True)
            self.append_response(self.chatgpt_text, f"Error: {str(e)}\n", error=True)
            self.battle_log += f"Error: {str(e)}\n\n"
        finally:
            self.root.after(0, lambda: self.submit_button.config(state='normal'))
            self.root.after(0, lambda: self.clear_button.config(state='normal'))
            self.root.after(0, lambda: self.save_button.config(state='normal'))
            self.root.after(0, lambda: self.stop_button.config(state='disabled'))

    def stop_battle_thread(self):
        self.stop_battle = True
        self.progress_label.config(text="Progress: Stopping...")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def call_xai_api(self, prompt, validate=False):
        headers = {
            "Authorization": f"Bearer {self.XAI_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.xai_model.get(),
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 50 if validate else None
        }
        response = requests.post(self.XAI_API_ENDPOINT, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def call_openai_api(self, prompt, validate=False):
        headers = {
            "Authorization": f"Bearer {self.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.openai_model.get(),
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 50 if validate else None
        }
        response = requests.post(self.OPENAI_API_ENDPOINT, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def update_response(self, text_widget, message):
        self.root.after(0, lambda: self._update_text_widget(text_widget, message, clear=True))

    def append_response(self, text_widget, message, error=False, tag=None):
        self.root.after(0, lambda: self._update_text_widget(text_widget, message, error=error, tag=tag))

    def _update_text_widget(self, text_widget, message, clear=False, error=False, tag=None):
        text_widget.config(state='normal')
        if clear:
            text_widget.delete(1.0, tk.END)
        if error:
            text_widget.insert(tk.END, message, "error")
        else:
            text_widget.insert(tk.END, message, tag)
        text_widget.config(state='disabled')
        text_widget.see(tk.END)

    def clear_text_widgets(self):
        for widget in [self.grok_text, self.chatgpt_text]:
            widget.config(state='normal')
            widget.delete(1.0, tk.END)
            widget.config(state='disabled')

    def clear_all(self):
        self.clear_text_widgets()
        self.query_entry.delete(0, tk.END)
        self.battle_log = ""
        self.progress_bar["value"] = 0
        self.progress_label.config(text="Progress: Waiting...")

    def save_battle(self):
        if not self.battle_log.strip():
            messagebox.showwarning("Warning", "No battle log to save!")
            return
        filepath = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(self.battle_log)
            messagebox.showinfo("Success", "Battle log saved!")

    def auto_save_battle(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"battle_log_{timestamp}.txt"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.battle_log)
        self.root.after(0, lambda: messagebox.showinfo("Auto-Save", f"Battle log saved as {filepath}"))

    def update_progress(self, fraction, final=False):
        progress = fraction * 100
        self.root.after(0, lambda: self.progress_bar.config(value=progress))
        if final:
            self.root.after(0, lambda: self.progress_label.config(text="Progress: Battle Complete!"))
        else:
            self.root.after(0, lambda: self.progress_label.config(text=f"Progress: {int(progress)}%"))

if __name__ == "__main__":
    root = tk.Tk()
    app = AIBattleApp(root)
    root.mainloop()
