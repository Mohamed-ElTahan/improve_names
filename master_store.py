import os
import sys
import pickle
import pandas as pd
from collections import defaultdict
from typing import Optional, Callable
from normalizer import normalize_for_matching

def get_base_dir() -> str:
    """الحصول على المجلد الأساسي للتطبيق سواء كان سكريبت أو ملف exe مستقل."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_cache_file_path() -> str:
    """مسار ملف الكاش المحلي داخل مجلد data المحمول بجانب التطبيق."""
    data_dir = os.path.join(get_base_dir(), 'data')
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, 'master_cache.pkl')

class MasterStore:
    def __init__(self):
        self.raw_names: list[str] = []
        self.normalized_names: list[str] = []
        # فهرس الاسم الأول: يربط كل اسم أول موحد بقائمة فهارس السجلات في raw_names
        self.first_name_index: dict[str, list[int]] = defaultdict(list)
        # خريطة سريعة للمطابقة التامة الفورية: normalized_name -> index
        self.exact_map: dict[str, int] = {}
        self.source_filename: str = ""
        self.total_records: int = 0

    @classmethod
    def load_from_cache(cls) -> Optional['MasterStore']:
        """تحميل الكاش المحفوظ مسبقاً إذا كان متوفراً."""
        cache_path = get_cache_file_path()
        if not os.path.exists(cache_path):
            return None
        try:
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
            store = cls()
            store.raw_names = data.get('raw_names', [])
            store.normalized_names = data.get('normalized_names', [])
            store.first_name_index = data.get('first_name_index', defaultdict(list))
            store.exact_map = data.get('exact_map', {})
            store.source_filename = data.get('source_filename', "")
            store.total_records = len(store.raw_names)
            return store
        except Exception as e:
            print(f"Error loading master cache: {e}")
            return None

    def save_to_cache(self):
        """حفظ الكاش الحالي في ملف محلي محمول."""
        cache_path = get_cache_file_path()
        data = {
            'raw_names': self.raw_names,
            'normalized_names': self.normalized_names,
            'first_name_index': dict(self.first_name_index),
            'exact_map': self.exact_map,
            'source_filename': self.source_filename,
        }
        with open(cache_path, 'wb') as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def build_from_excel(cls, excel_path: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> 'MasterStore':
        """
        قراءة ملف Excel (العمود الأول Column A) وبناء الفهرس والكاش.
        progress_callback: دالة تأخذ (current, total) لتحديث واجهة المستخدم.
        """
        # قراءة العمود الأول فقط بسرعة
        df = pd.read_excel(excel_path, header=None, usecols=[0])
        # تحويل القيم إلى نصوص واستبعاد القيم الفارغة
        series = df.iloc[:, 0].dropna().astype(str).str.strip()
        
        store = cls()
        store.source_filename = os.path.basename(excel_path)
        
        raw_list = []
        norm_list = []
        fn_index = defaultdict(list)
        exact_map = {}
        
        total = len(series)
        
        for idx, val in enumerate(series):
            raw_name = val.strip()
            if not raw_name:
                continue
                
            norm_name = normalize_for_matching(raw_name)
            if not norm_name:
                continue
                
            current_pos = len(raw_list)
            raw_list.append(raw_name)
            norm_list.append(norm_name)
            
            # الفهرس اللحظي للمطابقة التامة
            if norm_name not in exact_map:
                exact_map[norm_name] = current_pos
                
            # استخراج الاسم الأول الموحد (مع مراعاة الأسماء المركبة مثل "عبد الله" أو "ابو بكر")
            tokens = norm_name.split()
            if len(tokens) >= 2 and tokens[0] in ('عبد', 'ابو'):
                first_token = f"{tokens[0]} {tokens[1]}"
            elif tokens:
                first_token = tokens[0]
            else:
                first_token = ""
                
            if first_token:
                fn_index[first_token].append(current_pos)
                
            if progress_callback and idx % 2000 == 0:
                progress_callback(idx, total)
                
        if progress_callback:
            progress_callback(total, total)
            
        store.raw_names = raw_list
        store.normalized_names = norm_list
        store.first_name_index = fn_index
        store.exact_map = exact_map
        store.total_records = len(raw_list)
        
        # حفظ الكاش محلياً
        store.save_to_cache()
        return store
