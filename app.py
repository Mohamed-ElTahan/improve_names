import os
import sys
import threading
import pandas as pd
import customtkinter as ctk
from tkinter import filedialog, messagebox
from rapidfuzz import fuzz

from master_store import MasterStore, get_base_dir
from matcher import NameMatcher
from normalizer import format_normalized_name
from exporter import export_results_to_excel

# تعيين إعدادات المظهر العام
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# لوحة الألوان العصرية (Modern Palette)
PALETTE = {
    "bg_card": ("#F8FAFC", "#1E293B"),
    "card_border": ("#E2E8F0", "#334155"),
    "primary": "#3B82F6",
    "primary_hover": "#2563EB",
    "master_btn": "#2563EB",                   # أزرق ملكي لخيار مطابقة الشيت الرئيسي
    "master_btn_hover": "#1D4ED8",
    "norm_btn": "#059669",                     # زمردي أنيق لخيار التوحيد الشامل المباشر
    "norm_btn_hover": "#047857",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "text_main": ("#0F172A", "#F8FAFC"),
    "text_muted": ("#64748B", "#94A3B8"),
    "text_hint": ("#94A3B8", "#64748B"),
    "badge_bg": ("#E0E7FF", "#312E81"),
    "badge_text": ("#3730A3", "#C7D2FE"),
    "stat_card": ("#F1F5F9", "#0F172A"),
}

class ModernArabicMatcherApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("⚡ برنامج مطابقة وتعديل الأسماء")
        self.minsize(800, 600)
        
        # فتح البرنامج بالشاشة الكاملة تلقائياً (Maximized)
        try:
            self.after(0, lambda: self.state("zoomed"))
        except Exception:
            self.geometry("1100x750")

        # المتغيرات الأساسية
        self.master_store: MasterStore | None = None
        self.input_file_path: str = ""
        self.is_processing: bool = False

        self._build_header()
        self._build_main_content()
        self._load_master_cache_on_start()

    def _build_header(self):
        """رأس التطبيق العصري مع العنوان والتبديل اللوني."""
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=30, pady=(20, 10))

        # الجانب الأيمن: العنوان الرئيسي والوصف
        text_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        text_box.pack(side="right", anchor="e")

        main_title = ctk.CTkLabel(
            text_box,
            text="🎯 نظام مطابقة وتصحيح الأسماء 🎯",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=PALETTE["text_main"]
        )
        main_title.pack(anchor="e")

        # الجانب الأيسر: زر التبديل بين الوضع المظلم والفاتح
        theme_btn = ctk.CTkSegmentedButton(
            header_frame,
            values=["🌙 داكن", "☀️ فاتح"],
            command=self._toggle_theme,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            height=32
        )
        theme_btn.set("🌙 داكن")
        theme_btn.pack(side="left", anchor="center")

    def _toggle_theme(self, choice):
        if "داكن" in choice:
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("Light")

    def _build_main_content(self):
        """محتوى الواجهة الرئيسي مقسم إلى خطوتين فقط مع زرين مستقلين للتنفيذ."""
        # استخدام إطار عادي ممتد بدون CTkScrollableFrame لإلغاء الفراغ السفلي وشريط التمرير غير الضروري
        self.scroll = ctk.CTkFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=25, pady=(0, 15))

        # -------------------------------------------------------------
        # الخطوة 1: الشيت الرئيسي
        # -------------------------------------------------------------
        card_1 = ctk.CTkFrame(
            self.scroll, 
            corner_radius=14, 
            fg_color=PALETTE["bg_card"], 
            border_width=1, 
            border_color=PALETTE["card_border"]
        )
        card_1.pack(fill="x", pady=10)

        c1_head = ctk.CTkFrame(card_1, fg_color="transparent")
        c1_head.pack(fill="x", padx=20, pady=(15, 8))

        badge_1 = ctk.CTkLabel(
            c1_head,
            text="الخطوة 1",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=PALETTE["badge_bg"],
            text_color=PALETTE["badge_text"],
            corner_radius=6,
            width=65,
            height=24
        )
        badge_1.pack(side="left")

        title_1 = ctk.CTkLabel(
            c1_head,
            text="الشيت الرئيسى (الاستقبال)",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=PALETTE["text_main"]
        )
        title_1.pack(side="right")

        c1_body = ctk.CTkFrame(card_1, fg_color="transparent")
        c1_body.pack(fill="x", padx=20, pady=(0, 15))

        self.master_status_card = ctk.CTkFrame(c1_body, fg_color=PALETTE["stat_card"], corner_radius=10)
        self.master_status_card.pack(fill="x", pady=(0, 12))

        self.master_status_label = ctk.CTkLabel(
            self.master_status_card,
            text="⏳ جارٍ التحقق من قاعدة البيانات المحلية المحفوظة...",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=PALETTE["warning"]
        )
        self.master_status_label.pack(anchor="e", padx=15, pady=10)

        c1_actions = ctk.CTkFrame(c1_body, fg_color="transparent")
        c1_actions.pack(fill="x")

        self.btn_select_master = ctk.CTkButton(
            c1_actions,
            text="📂 اختيار / تحديث الشيت الرئيسي",
            command=self._on_choose_master,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=PALETTE["primary"],
            hover_color=PALETTE["primary_hover"],
            height=38,
            corner_radius=8
        )
        self.btn_select_master.pack(side="left")

        # -------------------------------------------------------------
        # الخطوة 2: الشيت المدخل
        # -------------------------------------------------------------
        card_2 = ctk.CTkFrame(
            self.scroll, 
            corner_radius=14, 
            fg_color=PALETTE["bg_card"], 
            border_width=1, 
            border_color=PALETTE["card_border"]
        )
        card_2.pack(fill="x", pady=10)

        c2_head = ctk.CTkFrame(card_2, fg_color="transparent")
        c2_head.pack(fill="x", padx=20, pady=(15, 8))

        badge_2 = ctk.CTkLabel(
            c2_head,
            text="الخطوة 2",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=PALETTE["badge_bg"],
            text_color=PALETTE["badge_text"],
            corner_radius=6,
            width=65,
            height=24
        )
        badge_2.pack(side="left")

        title_2 = ctk.CTkLabel(
            c2_head,
            text="الملف المطلوب مطابقته أو تعديله",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=PALETTE["text_main"]
        )
        title_2.pack(side="right")

        c2_body = ctk.CTkFrame(card_2, fg_color="transparent")
        c2_body.pack(fill="x", padx=20, pady=(0, 15))

        self.input_file_box = ctk.CTkFrame(c2_body, fg_color=PALETTE["stat_card"], corner_radius=10)
        self.input_file_box.pack(fill="x", pady=(0, 12))

        self.input_file_label = ctk.CTkLabel(
            self.input_file_box,
            text="📄 لم يتم تحديد ملف إدخال بعد (يشترط وجود الأسماء في العمود الأول )",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=PALETTE["text_muted"]
        )
        self.input_file_label.pack(anchor="e", padx=15, pady=10)

        c2_actions = ctk.CTkFrame(c2_body, fg_color="transparent")
        c2_actions.pack(fill="x")

        self.btn_select_input = ctk.CTkButton(
            c2_actions,
            text= "اختار شيت الاسماء",
            command=self._on_choose_input,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=PALETTE["primary"],
            hover_color=PALETTE["primary_hover"],
            height=38,
            corner_radius=8
        )
        self.btn_select_input.pack(side="left")

        # -------------------------------------------------------------
        # لوحة التنفيذ المزدوجة (زران مستقلان بحسب الوظيفة)
        # -------------------------------------------------------------
        action_card = ctk.CTkFrame(
            self.scroll, 
            corner_radius=14, 
            fg_color=PALETTE["bg_card"], 
            border_width=1, 
            border_color=PALETTE["card_border"]
        )
        action_card.pack(fill="x", pady=10)

        ac_body = ctk.CTkFrame(action_card, fg_color="transparent")
        ac_body.pack(fill="x", padx=20, pady=20)

        # شريط التقدم
        self.progress_bar = ctk.CTkProgressBar(
            ac_body,
            height=14,
            corner_radius=7,
            progress_color=PALETTE["norm_btn"]
        )
        self.progress_bar.pack(fill="x", pady=(5, 10))
        self.progress_bar.set(0)

        # سطر تفاصيل الإنجاز
        status_row = ctk.CTkFrame(ac_body, fg_color="transparent")
        status_row.pack(fill="x", pady=(0, 15))

        self.progress_pct_label = ctk.CTkLabel(
            status_row,
            text="0%",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=PALETTE["norm_btn"]
        )
        self.progress_pct_label.pack(side="left")

        self.progress_status_label = ctk.CTkLabel(
            status_row,
            text="جاهز للبدء — اختر طريقة المعالجة المطلوبة بالأسفل",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=PALETTE["text_muted"]
        )
        self.progress_status_label.pack(side="right")

        # حاوية الزرين جنباً إلى جنب
        btns_row = ctk.CTkFrame(ac_body, fg_color="transparent")
        btns_row.pack(fill="x", pady=(5, 10))
        btns_row.grid_columnconfigure((0, 1), weight=1)

        # 1. زر المطابقة مع الشيت الرئيسي (يعتمد على قاعدة الشيت الرئيسي + نسبة التطابق)
        self.btn_match_master = ctk.CTkButton(
            btns_row,
            text= " مطابقة الاسم من الشيت الرائيسى",
            command=self._start_master_matching,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=PALETTE["master_btn"],
            hover_color=PALETTE["master_btn_hover"],
            height=54,
            corner_radius=10
        )
        self.btn_match_master.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        # 2. زر التوحيد المباشر المستقل (يعدل اسم الإدخال نفسه بقواعد التوحيد + نسبة التغيير)
        self.btn_match_norm = ctk.CTkButton(
            btns_row,
            text="✨ توحيد كتابة الأسماء",
            command=self._start_direct_normalization,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=PALETTE["norm_btn"],
            hover_color=PALETTE["norm_btn_hover"],
            height=54,
            corner_radius=10
        )
        self.btn_match_norm.grid(row=0, column=1, padx=(8, 0), sticky="ew")

        # شريط تلميحات القواعد - تم حذفه لإلغاء المساحة الفارغة في الأسفل


    def _load_master_cache_on_start(self):
        """تحميل الكاش تلقائياً عند فتح التطبيق."""
        self.master_store = MasterStore.load_from_cache()
        if self.master_store and self.master_store.total_records > 0:
            msg = f"✅ الشيت الرئيسي جاهز ومحمل مسبقاً: {self.master_store.total_records:,} اسم مسجل ({self.master_store.source_filename})"
            self.master_status_label.configure(text=msg, text_color=PALETTE["norm_btn"])
        else:
            msg = "⚠️ لا توجد قاعدة بيانات رئيسية مسجلة حالياً (اختياري، تحتاجه فقط عند زر المطابقة مع الشيت الرئيسي)."
            self.master_status_label.configure(text=msg, text_color=PALETTE["warning"])

    def _on_choose_master(self):
        file_path = filedialog.askopenfilename(
            title="اختر ملف الشيت الرئيسي (Excel)",
            filetypes=[("Excel Files", "*.xlsx *.xls")]
        )
        if not file_path:
            return

        def task():
            self._set_ui_state(processing=True)
            self.master_status_label.configure(
                text="⚡ جارٍ قراءة وفهرسة الشيت الرئيسي وحفظه في الذاكرة المحلية...", 
                text_color=PALETTE["warning"]
            )
            self.progress_bar.set(0)

            def update_progress(curr, total):
                if total > 0:
                    pct = curr / total
                    self.after(0, lambda: self.progress_bar.set(pct))
                    self.after(0, lambda: self.progress_pct_label.configure(text=f"{int(pct * 100)}%"))
                    self.after(0, lambda: self.progress_status_label.configure(
                        text=f"جارٍ الفهرسة: تم استيعاب {curr:,} من أصل {total:,} اسم..."
                    ))

            try:
                store = MasterStore.build_from_excel(file_path, progress_callback=update_progress)
                self.master_store = store
                success_msg = f"✅ تم حفظ وفهرسة الشيت الرئيسي بنجاح: {store.total_records:,} اسم ({store.source_filename})"
                self.after(0, lambda: self.master_status_label.configure(text=success_msg, text_color=PALETTE["norm_btn"]))
                self.after(0, lambda: self.progress_status_label.configure(text="اكتملت الفهرسة والحفظ بنجاح!"))
                self.after(0, lambda: self.progress_bar.set(1.0))
                self.after(0, lambda: self.progress_pct_label.configure(text="100%"))
                messagebox.showinfo("تم بنجاح 🎉", f"تمت فهرسة وحفظ الشيت الرئيسي بنجاح تام!\nإجمالي الأسماء المفهرسة: {store.total_records:,} اسم.")
            except Exception as e:
                err_msg = f"❌ خطأ أثناء معالجة الشيت الرئيسي: {e}"
                self.after(0, lambda: self.master_status_label.configure(text=err_msg, text_color=PALETTE["danger"]))
                messagebox.showerror("خطأ", f"تعذر قراءة وفهرسة الشيت الرئيسي:\n{e}")
            finally:
                self._set_ui_state(processing=False)

        threading.Thread(target=task, daemon=True).start()

    def _on_choose_input(self):
        file_path = filedialog.askopenfilename(
            title="اختر ملف الإدخال المطلوب تعديله (Excel)",
            filetypes=[("Excel Files", "*.xlsx *.xls")]
        )
        if file_path:
            self.input_file_path = file_path
            self.input_file_label.configure(
                text=f"📁 تم تحديد الملف: {os.path.basename(file_path)}",
                text_color=PALETTE["norm_btn"]
            )

    def _set_ui_state(self, processing: bool):
        """تفعيل أو تعطيل الأزرار أثناء المعالجة."""
        self.is_processing = processing
        state = "disabled" if processing else "normal"
        self.after(0, lambda: self.btn_select_master.configure(state=state))
        self.after(0, lambda: self.btn_select_input.configure(state=state))
        self.after(0, lambda: self.btn_match_master.configure(state=state))
        self.after(0, lambda: self.btn_match_norm.configure(state=state))

    def _start_master_matching(self):
        """المطابقة مع الشيت الرئيسي (المسار الأول)."""
        if not self.master_store or self.master_store.total_records == 0:
            messagebox.showwarning("تنبيه", "لاستخدام زر المطابقة، يرجى أولاً اختيار وفهرسة الشيت الرئيسي في الخطوة 1!")
            return

        if not self.input_file_path or not os.path.exists(self.input_file_path):
            messagebox.showwarning("تنبيه", "يرجى اختيار ملف الإدخال المطلوب مطابقته في الخطوة 2!")
            return

        if self.is_processing:
            return

        default_out_name = f"مطابقة_الشيت_الرئيسي_{os.path.splitext(os.path.basename(self.input_file_path))[0]}.xlsx"
        output_file_path = filedialog.asksaveasfilename(
            title="حفظ ملف نتائج المطابقة باسم",
            initialfile=default_out_name,
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")]
        )
        if not output_file_path:
            return

        self._set_ui_state(processing=True)

        def worker():
            try:
                self.after(0, lambda: self.progress_status_label.configure(text="جارٍ قراءة وفحص أسماء ملف الإدخال..."))
                self.after(0, lambda: self.progress_bar.set(0))
                self.after(0, lambda: self.progress_pct_label.configure(text="0%"))

                df = pd.read_excel(self.input_file_path, header=None, usecols=[0])
                input_series = df.iloc[:, 0].fillna("").astype(str).tolist()

                total_rows = len(input_series)
                matcher = NameMatcher(self.master_store)
                results = []

                for idx, raw_val in enumerate(input_series):
                    orig_name = raw_val.strip()
                    if not orig_name:
                        matched_name, score = "", 0.0
                    else:
                        matched_name, score = matcher.match_name(orig_name, output_mode="master")

                    results.append({
                        'original': orig_name,
                        'matched': matched_name,
                        'score': score
                    })

                    if (idx + 1) % 15 == 0 or idx == total_rows - 1:
                        pct = (idx + 1) / total_rows
                        curr = idx + 1
                        self.after(0, lambda p=pct, c=curr: self._update_ui_progress(p, c, total_rows))

                self.after(0, lambda: self.progress_status_label.configure(text="جارٍ تصدير ورقة العمل وتلوين النتائج..."))
                export_results_to_excel(results, output_file_path, mode="master")

                self.after(0, lambda: self.progress_status_label.configure(text="✨ تم إنجاز المطابقة والتصدير بنجاح!"))
                self.after(0, lambda: self.progress_bar.set(1.0))
                self.after(0, lambda: self.progress_pct_label.configure(text="100%"))

                msg = f"🎉 تم الانتهاء بنجاح من المطابقة مع الشيت الرئيسي!\n\n📂 مسار الحفظ:\n{output_file_path}\n\nهل ترغب في فتح ملف Excel الآن لمراجعة النتائج؟"
                if messagebox.askyesno("اكتمل العمل بنجاح", msg):
                    try:
                        os.startfile(output_file_path)
                    except Exception as ex:
                        messagebox.showwarning("تنبيه", f"تعذر فتح الملف تلقائياً: {ex}")

            except Exception as e:
                self.after(0, lambda: self.progress_status_label.configure(text=f"❌ حدث خطأ غير متوقع: {e}"))
                messagebox.showerror("خطأ", f"حدث خطأ أثناء تنفيذ العملية:\n{e}")
            finally:
                self._set_ui_state(processing=False)

        threading.Thread(target=worker, daemon=True).start()

    def _start_direct_normalization(self):
        """التوحيد المباشر والمستقل لأسماء الإدخال فقط بقواعد التوحيد (المسار الثاني)."""
        if not self.input_file_path or not os.path.exists(self.input_file_path):
            messagebox.showwarning("تنبيه", "يرجى اختيار ملف الإدخال المطلوب توحيده وتعديله في الخطوة 2!")
            return

        if self.is_processing:
            return

        default_out_name = f"أسماء_موحدة_مباشرة_{os.path.splitext(os.path.basename(self.input_file_path))[0]}.xlsx"
        output_file_path = filedialog.asksaveasfilename(
            title="حفظ ملف الأسماء الموحدة باسم",
            initialfile=default_out_name,
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")]
        )
        if not output_file_path:
            return

        self._set_ui_state(processing=True)

        def worker():
            try:
                self.after(0, lambda: self.progress_status_label.configure(text="جارٍ قراءة وتوحيد الأسماء بقواعد التوحيد الشاملة..."))
                self.after(0, lambda: self.progress_bar.set(0))
                self.after(0, lambda: self.progress_pct_label.configure(text="0%"))

                df = pd.read_excel(self.input_file_path, header=None, usecols=[0])
                input_series = df.iloc[:, 0].fillna("").astype(str).tolist()

                total_rows = len(input_series)
                results = []

                for idx, raw_val in enumerate(input_series):
                    orig_name = raw_val.strip()
                    if not orig_name:
                        matched_name, lit_score = "", 0.0
                    else:
                        # تطبيق قواعد التوحيد الشاملة مباشرة على اسم الإدخال
                        matched_name = format_normalized_name(orig_name)
                        
                        # حساب نسبة التطابق الحرفي الفعلية:
                        # إذا كان الاسم مطابقاً حرفياً ولم يتغير فيه أي حرف تكون 100%
                        # إذا تغير أ إلى ا أو ي إلى ى أو فصل مركب، تتأثر النسبة الفعلية وتتغير
                        if orig_name == matched_name:
                            lit_score = 100.0
                        else:
                            lit_score = round(fuzz.ratio(orig_name, matched_name), 1)

                    results.append({
                        'original': orig_name,
                        'matched': matched_name,
                        'score': lit_score
                    })

                    if (idx + 1) % 50 == 0 or idx == total_rows - 1:
                        pct = (idx + 1) / total_rows
                        curr = idx + 1
                        self.after(0, lambda p=pct, c=curr: self._update_ui_progress(p, c, total_rows))

                self.after(0, lambda: self.progress_status_label.configure(text="جارٍ تصدير ورقة العمل وتلوين الأسماء المعدلة..."))
                export_results_to_excel(results, output_file_path, mode="normalized")

                self.after(0, lambda: self.progress_status_label.configure(text="✨ تم إنجاز التوحيد المباشر بنجاح!"))
                self.after(0, lambda: self.progress_bar.set(1.0))
                self.after(0, lambda: self.progress_pct_label.configure(text="100%"))

                msg = f"🎉 تم الانتهاء بنجاح من توحيد كتابة الأسماء مباشرة دون الاعتماد على الشيت الرئيسي!\n\n📂 مسار الحفظ:\n{output_file_path}\n\nهل ترغب في فتح ملف Excel الآن لمراجعة النتائج؟"
                if messagebox.askyesno("اكتمل العمل بنجاح", msg):
                    try:
                        os.startfile(output_file_path)
                    except Exception as ex:
                        messagebox.showwarning("تنبيه", f"تعذر فتح الملف تلقائياً: {ex}")

            except Exception as e:
                self.after(0, lambda: self.progress_status_label.configure(text=f"❌ حدث خطأ غير متوقع: {e}"))
                messagebox.showerror("خطأ", f"حدث خطأ أثناء تنفيذ العملية:\n{e}")
            finally:
                self._set_ui_state(processing=False)

        threading.Thread(target=worker, daemon=True).start()

    def _update_ui_progress(self, pct: float, current: int, total: int):
        self.progress_bar.set(pct)
        self.progress_pct_label.configure(text=f"{int(pct * 100)}%")
        self.progress_status_label.configure(text=f"جارٍ المعالجة: تمت معالجة {current:,} من {total:,} اسم")

if __name__ == "__main__":
    app = ModernArabicMatcherApp()
    app.mainloop()
