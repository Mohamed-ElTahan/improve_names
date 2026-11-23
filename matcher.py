from rapidfuzz import fuzz
from normalizer import normalize_for_matching, format_normalized_name
from master_store import MasterStore
from typing import Tuple, Optional

def get_name_parts(normalized_name: str) -> list[str]:
    """
    تقسيم الاسم الموحد إلى مقاطع الأسماء الحقيقية مع دمج الأسماء المركبة:
    - 'عبد الله' تعتبر اسماً واحداً (المقطع الأول).
    - 'ابو بكر' تعتبر اسماً واحداً.
    - 'صلاح الدين' تعتبر اسماً واحداً.
    - 'عطا الله' تعتبر اسماً واحداً.
    """
    raw_tokens = normalized_name.split()
    parts = []
    i = 0
    n = len(raw_tokens)
    while i < n:
        t = raw_tokens[i]
        # 1. الأسماء المركبة التي تبدأ بـ 'عبد' أو 'ابو'
        if t in ('عبد', 'ابو') and i + 1 < n:
            parts.append(f"{t} {raw_tokens[i+1]}")
            i += 2
        # 2. الأسماء المركبة التي تنتهي بـ 'الدين' أو 'الله'
        elif i + 1 < n and raw_tokens[i+1] in ('الدين', 'الله'):
            parts.append(f"{t} {raw_tokens[i+1]}")
            i += 2
        else:
            parts.append(t)
            i += 1
    return parts

def extract_first_name(normalized_name: str) -> str:
    """استخراج الاسم الأول الموحد مع مراعاة المركبات."""
    parts = get_name_parts(normalized_name)
    return parts[0] if parts else ""

class NameMatcher:
    def __init__(self, master_store: MasterStore):
        self.store = master_store
        self.all_first_names = list(master_store.first_name_index.keys())

    def match_name(self, query_raw: str, output_mode: str = "master") -> Tuple[str, float]:
        """
        مطابقة اسم قادم من الشيت المدخل:
        1. تطبيق شرط أمان إلزامي: تطابق تام لأول 3 أسماء على الأقل بعد التوحيد.
        2. إذا لم يتطابق أول 3 أسماء أو لم يكن موجوداً:
           يُترك 'الاسم المعدل' فارغاً تماماً ("") ونسبة التطابق تكون 0.0% (تلوين أحمر).
        3. إذا تحقق شرط أول 3 أسماء:
           تحسب نسبة التطابق الحرفي الفعلية بين الاسم الأصلي المدخل والاسم الناتج:
           بحيث إذا كان هناك أي حرف تغير (أ إلى ا، ي إلى ى، ة إلى ه، أو فصل مسافة)،
           تظهر النسبة الفعلية وتتأثر بالحروف المتغيرة (مثلاً 83.3% أو 91.7%) ولا تكون 100% إلا إذا كان الاسم متطابقاً حرفياً بدون أي تغيير.
        """
        if not query_raw or not str(query_raw).strip():
            return ("", 0.0)
            
        raw_text = str(query_raw).strip()
        query_norm = normalize_for_matching(raw_text)
        if not query_norm:
            return ("", 0.0)

        # استخراج مقاطع الاسم المدخل
        q_parts = get_name_parts(query_norm)
        if len(q_parts) < 3:
            # إذا كان الاسم المدخل ثنائياً فقط ولا يوجد له تطابق تام في الشيت الرئيسي
            if query_norm in self.store.exact_map:
                idx = self.store.exact_map[query_norm]
                return self._format_result(raw_text, idx, output_mode)
            return ("", 0.0)

        q_first = q_parts[0]
        q_second = q_parts[1]
        q_third = q_parts[2]

        candidate_indices = []
        if q_first in self.store.first_name_index:
            candidate_indices = self.store.first_name_index[q_first]

        if not candidate_indices:
            return ("", 0.0)

        best_idx: Optional[int] = None
        best_norm_score: float = -1.0

        # فحص المرشحين وتطبيق الشرط الإلزامي: تطابق تام 100% لأول 3 أسماء
        for idx in candidate_indices:
            cand_norm = self.store.normalized_names[idx]
            cand_parts = get_name_parts(cand_norm)

            if len(cand_parts) < 3:
                continue

            # التحقق الصارم: هل أول 3 أسماء متطابقون تماماً بعد التوحيد؟
            if cand_parts[0] == q_first and cand_parts[1] == q_second and cand_parts[2] == q_third:
                # اختيار المرشح الأقرب للاسم المطلوب
                score = fuzz.token_sort_ratio(query_norm, cand_norm)
                if score > best_norm_score:
                    best_norm_score = float(score)
                    best_idx = idx
                    if best_norm_score == 100.0:
                        break

        # إذا وُجد مرشح يحقق شرط أول 3 أسماء بنجاح
        if best_idx is not None and best_norm_score >= 70.0:
            return self._format_result(raw_text, best_idx, output_mode)

        # إذا لم يتحقق الشرط نهائياً: يترك فارغاً بنسبة 0.0%
        return ("", 0.0)

    def _format_result(self, raw_input: str, master_idx: int, output_mode: str) -> Tuple[str, float]:
        """
        تنسيق الاسم الناتج وحساب نسبة التطابق الحرفي الفعلية:
        أي تغيير في الحروف (أ إلى ا، ي إلى ى، فصل مركب) يؤثر في النسبة لتعكس التغيير الحاصل بدقة.
        """
        raw_master = self.store.raw_names[master_idx]
        if output_mode == "normalized":
            res_name = format_normalized_name(raw_master)
        else:
            res_name = raw_master

        # حساب النسبة الحرفية الفعلية بين المدخل والاسم الناتج
        if raw_input == res_name:
            literal_score = 100.0
        else:
            literal_score = round(fuzz.ratio(raw_input, res_name), 1)

        return (res_name, literal_score)
