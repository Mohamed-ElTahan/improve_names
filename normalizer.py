import re
import unicodedata

# علامات التشكيل والتطويل في اللغة العربية
TASHKEEL_REGEX = re.compile(r'[\u0617-\u061A\u064B-\u0652]')
TATWEEL_CHAR = '\u0640'

# أسماء التركيب الشائعة مع لفظ الجلالة "الله"
ALLAH_PREFIXES = [
    'عطا', 'عطاء', 'نصر', 'سعد', 'فتح', 'فضل', 'فرج', 'عوض', 'كرم', 'جاد', 
    'رزق', 'ضيف', 'خلف', 'خلق', 'جار', 'حسب', 'رحمة', 'هبة', 'نعمة', 'منة',
    'امانة', 'بركة', 'عزة', 'قدرة', 'لطف', 'امر', 'خير', 'شكر', 'عبيد', 'عبد'
]

def split_compound_names(text: str) -> str:
    """
    فصل جميع أنواع الأسماء المركبة بمسافة:
    - عبد + الاسم (عبدالله -> عبد الله، عبدالرحمن -> عبد الرحمن)
    - ابو + الاسم (ابوبكر -> ابو بكر، ابوالعلا -> ابو العلا)
    - اسم + الدين (صلاحالدين -> صلاح الدين، سيفالدين -> سيف الدين)
    - اسم + الله (عطاالله -> عطا الله، نصرالله -> نصر الله)
    """
    words = text.split()
    processed_words = []
    
    for word in words:
        w = word
        
        # 1. فصل بادئة "عبد" إذا كانت ملتصقة (مثال: عبدالله، عبدالرحمن، عبدالعزيز، عبدربه)
        if w.startswith('عبد') and len(w) > 3 and not w.startswith('عبد '):
            w = 'عبد ' + w[3:].strip()
            
        # 2. فصل بادئة "ابو" إذا كانت ملتصقة (مثال: ابوبكر، ابوالعلا، ابوالخير)
        elif (w.startswith('ابو') or w.startswith('أبو')) and len(w) > 3:
            remainder = w[3:].strip()
            if remainder:
                w = 'ابو ' + remainder
            
        # 3. فصل لاحقة "الدين" إذا كانت ملتصقة (مثال: صلاحالدين -> صلاح الدين، علاءالدين -> علاء الدين)
        elif w.endswith('الدين') and len(w) > 5 and not w.endswith(' الدين'):
            prefix = w[:-5]
            if len(prefix) >= 2:
                w = prefix + ' الدين'

        # 4. فصل لاحقة "الله" إذا كانت ملتصقة (مثال: عطاالله -> عطا الله، نصرالله -> نصر الله)
        elif w.endswith('الله') and len(w) > 4 and not w.endswith(' الله'):
            prefix = w[:-4]
            clean_p = prefix.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ء', '')
            if any(clean_p.startswith(pfx) or clean_p == pfx for pfx in ALLAH_PREFIXES):
                w = prefix + ' الله'
                
        processed_words.append(w)
        
    return ' '.join(processed_words)

def clean_arabic_text(text: str) -> str:
    """تنظيف النص من الحركات، التطويل، والرموز الزائدة وتوحيد المسافات."""
    if not text or not isinstance(text, str):
        return ""
    
    # إزالة التشكيل
    text = TASHKEEL_REGEX.sub('', text)
    # إزالة التطويل
    text = text.replace(TATWEEL_CHAR, '')
    # إزالة علامات الترقيم والأقواس والأرقام والشرطات وأي رموز غريبة
    text = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', text)
    text = re.sub(r'[\d٠-٩_]', ' ', text)
    # توحيد المسافات الزائدة
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def normalize_for_matching(text: str) -> str:
    """
    تطبيق قواعد التوحيد الصارمة للمطابقة والمقارنة الرياضية:
    1. تنظيف الحركات والتطويل والرموز.
    2. توحيد الهمزات والألفات (أ, إ, آ, ٱ -> ا).
    3. فصل جميع الأسماء المركبة (عبد، ابو، الدين، الله) بمسافة إجبارية.
    4. توحيد كتابة 'أبو' إلى 'ابو'.
    5. توحيد التاء المربوطة (ة -> ه).
    6. تحويل الياء في نهاية الكلمات إلى ألف مقصورة (ي -> ى).
    """
    cleaned = clean_arabic_text(text)
    if not cleaned:
        return ""
    
    # توحيد الألفات في البداية لتسهيل مطابقة البادئات بدقة
    cleaned = re.sub(r'[أإآٱ]', 'ا', cleaned)
    
    # فصل كافة الأسماء المركبة
    spaced = split_compound_names(cleaned)
    
    # إعادة تفكيك وتطبيق القواعد على الكلمات
    words = spaced.split()
    normalized_words = []
    
    for word in words:
        w = word
        # توحيد الألفات
        w = re.sub(r'[أإآٱ]', 'ا', w)
        # توحيد التاء المربوطة إلى هاء
        w = w.replace('ة', 'ه')
        # تحويل الياء في نهاية الكلمة إلى ألف مقصورة (ى)
        if w.endswith('ي'):
            w = w[:-1] + 'ى'
        normalized_words.append(w)
        
    return ' '.join(normalized_words)

def format_normalized_name(text: str) -> str:
    """
    تنسيق الاسم بصيغة الإخراج الموحدة (Normalized Spelling):
    يطبق قواعد توحيد الهمزات (ا)، كتابة (ابو) بدون همزة وبمسافة،
    فصل (عبد ) و ( الدين) و ( الله)، وتحويل (ي) النهائية إلى (ى)، و (ة) إلى (ه).
    """
    return normalize_for_matching(text)
