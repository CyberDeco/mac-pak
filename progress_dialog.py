#!/usr/bin/env python3
"""
Progress dialog for long-running operations
"""

import tkinter as tk
from tkinter import ttk, messagebox

class ProgressDialog:
    """Progress dialog with better UI responsiveness"""
    
    def __init__(self, parent, title="Processing..."):
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x150")
        self.dialog.resizable(False, False)
        
        # Center the dialog
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Make it modal and prevent closing during operation
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)
        
        self.setup_ui()
        self.cancelled = False
        self.last_update_time = 0
        self.update_frequency = 0.1  # Update at most 10 times per second
    
    def setup_ui(self):
        """Setup the progress dialog UI"""
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill='both', expand=True)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Initializing...")
        self.status_label.pack(pady=(0, 10))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame, 
            mode='determinate',
            variable=self.progress_var,
            length=350
        )
        self.progress_bar.pack(pady=(0, 10))
        
        # Percentage label
        self.percent_label = ttk.Label(main_frame, text="0%")
        self.percent_label.pack(pady=(0, 10))
        
        # Cancel button
        self.cancel_button = ttk.Button(main_frame, text="Cancel", command=self.on_cancel)
        self.cancel_button.pack()
        
        # Center the dialog on parent
        self.center_dialog()
    
    def center_dialog(self):
        """Center the dialog on the parent window"""
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def update_progress(self, percentage, status_text=""):
        """Update progress with throttling to prevent UI lag"""
        if self.cancelled:
            return False
        
        import time
        current_time = time.time()
        
        # Throttle updates to prevent UI lag
        if current_time - self.last_update_time < self.update_frequency and percentage != 100:
            return True
        
        self.last_update_time = current_time
        
        try:
            self.progress_var.set(min(100, max(0, percentage)))
            self.percent_label.config(text=f"{int(percentage)}%")
            
            if status_text:
                # Truncate very long status text
                if len(status_text) > 50:
                    status_text = status_text[:47] + "..."
                self.status_label.config(text=status_text)
            
            # Force update but limit frequency
            self.dialog.update_idletasks()
            
        except tk.TclError:
            # Dialog might be closed
            return False
        
        return True
    
    def on_cancel(self):
        """Handle cancel button with confirmation"""
        if not self.cancelled:
            result = messagebox.askyesno("Cancel Operation", 
                                       "Are you sure you want to cancel this operation?",
                                       parent=self.dialog)
            if result:
                self.cancelled = True
                self.status_label.config(text="Cancelling...")
                self.cancel_button.config(state='disabled')
    
    def is_cancelled(self):
        """Check if operation was cancelled"""
        return self.cancelled
    
    def close(self):
        """Close the dialog safely"""
        try:
            if not self.cancelled:
                self.dialog.destroy()
        except tk.TclError:
            pass  # Dialog already closed