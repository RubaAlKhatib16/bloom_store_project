from flask import Blueprint, request, jsonify
import re
import unicodedata

chatbot_bp = Blueprint('chatbot', __name__)


def is_arabic(text):
    """Detect if text contains Arabic characters."""
    arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
    return bool(arabic_pattern.search(text))


def clean_text(text):
    """Remove punctuation and normalize spaces."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text


# ============================================================
# KNOWLEDGE BASE — keyword → (reply_en, reply_ar, link, label)
# ============================================================

RULES = [
    # --- Birthday ---
    {
        "keywords": ["birthday", "bday", "happy birthday", "born", "عيد ميلاد", "ميلاد"],
        "reply_en": "🎂 Birthdays deserve the most vibrant blooms! Explore our joyful birthday bouquets filled with roses, sunflowers, and cheerful colors.",
        "reply_ar": "🎂 عيد الميلاد يستحق أكثر الزهور حيوية! اكتشف باقات عيد الميلاد السعيدة المليئة بالورود، وعباد الشمس، والألوان المبهجة.",
        "link": "/occasion/birthday",
        "label_en": "Birthday Bouquets",
        "label_ar": "باقات عيد الميلاد"
    },
    # --- Graduation ---
    {
        "keywords": ["graduation", "graduate", "grad", "university", "school", "تخرج", "شهادة"],
        "reply_en": "🎓 Celebrate achievements with our elegant graduation bouquets — designed to make every success unforgettable.",
        "reply_ar": "🎓 احتفل بالإنجازات مع باقات التخرج الأنيقة — مصممة لجعل كل نجاح لا يُنسى.",
        "link": "/occasion/graduation",
        "label_en": "Graduation Bouquets",
        "label_ar": "باقات التخرج"
    },
    # --- Wedding ---
    {
        "keywords": ["wedding", "bridal", "bride", "marriage", "marry", "زفاف", "عروس", "زواج"],
        "reply_en": "💍 Discover luxurious bridal bouquets crafted with timeless elegance for your special wedding day.",
        "reply_ar": "💍 اكتشفي باقات الزفاف الفاخرة المصممة بأناقة خالدة ليوم زفافك المميز.",
        "link": "/occasion/wedding",
        "label_en": "Wedding Collection",
        "label_ar": "باقات الزفاف"
    },
    # --- Mother's Day ---
    {
        "keywords": ["mother", "mom", "mum", "mama", "mothers day", "mother's day", "أم", "أمي", "عيد الأم"],
        "reply_en": "💐 Surprise your mother with soft pink roses, lilies, and elegant arrangements made with love.",
        "reply_ar": "💐 فاجئ والدتك بالورود الوردية الناعمة والزنابق والترتيبات الأنيقة المصنوعة بحب.",
        "link": "/occasion/mothers-day",
        "label_en": "Mother's Day Bouquets",
        "label_ar": "باقات عيد الأم"
    },
    # --- Valentine / Love ---
    {
        "keywords": ["valentine", "love", "romantic", "romance", "heart", "beloved", "حب", "فالنتاين", "قلب", "رومانسي"],
        "reply_en": "❤️ Romantic flowers that speak from the heart. Explore our stunning Valentine bouquets.",
        "reply_ar": "❤️ زهور رومانسية تتحدث من القلب. استكشف باقات فالنتاين الرائعة.",
        "link": "/occasion/love",
        "label_en": "Valentine Collection",
        "label_ar": "باقات عيد الحب"
    },
    # --- Sorry / Apology ---
    {
        "keywords": ["sorry", "apology", "apologize", "forgive", "forgiveness", "make up", "آسف", "اعتذار", "معذرة"],
        "reply_en": "🌸 Flowers can heal hearts. Send a thoughtful apology bouquet to express your feelings beautifully.",
        "reply_ar": "🌸 الزهور يمكنها أن تشفي القلوب. أرسل باقة اعتذار معبرة لتعبر عن مشاعرك بشكل جميل.",
        "link": "/occasion/sorry",
        "label_en": "Sorry Bouquets",
        "label_ar": "باقات الاعتذار"
    },
    # --- New Baby ---
    {
        "keywords": ["baby", "newborn", "new baby", "birth", "born", "مولود", "طفل", "ولادة", "مولود جديد", "طفل جديد", "وليد"],
        "reply_en": "👶 Welcome the little one with delicate and joyful flower arrangements full of warmth and happiness.",
        "reply_ar": "👶 رحب بالصغير بتشكيلات زهور رقيقة ومبهجة مليئة بالدفء والسعادة.",
        "link": "/occasion/new-baby",
        "label_en": "New Baby Bouquets",
        "label_ar": "باقات المولود الجديد"
    },
    # --- Anniversary ---
    {
        "keywords": ["anniversary", "years together", "ذكرى", "ذكرى سنوية"],
        "reply_en": "🥂 Celebrate love and memories with our romantic anniversary flower collection.",
        "reply_ar": "🥂 احتفل بالحب والذكريات مع مجموعة الزهور الرومانسية للذكرى السنوية.",
        "link": "/occasion/anniversary",
        "label_en": "Anniversary Bouquets",
        "label_ar": "باقات الذكرى السنوية"
    },
    # --- Ramadan & Eid ---
    {
        "keywords": ["ramadan", "eid", "رمضان", "الفطر"],
        "reply_en": "🌙 Elegant Ramadan bouquets inspired by warmth, generosity, and beautiful festive moments.",
        "reply_ar": "🌙 باقات رمضان الأنيقة المستوحاة من الدفء والكرم ولحظات الأعياد الجميلة.",
        "link": "/occasion/ramadan",
        "label_en": "Ramadan Collection",
        "label_ar": "باقات رمضان"
    },
    # --- Get Well Soon ---
    {
        "keywords": ["get well", "sick", "hospital", "recovery", "شفاء", "مريض", "سلامتك"],
        "reply_en": "🌼 Brighten someone's recovery journey with uplifting and cheerful get well soon bouquets.",
        "reply_ar": "🌼 أضئ رحلة الشفاء لشخص ما بباقات \"أتمنى لك الشفاء العاجل\" المبهجة والمشرقة.",
        "link": "/occasion/get-well-soon",
        "label_en": "Get Well Soon",
        "label_ar": "باقات السلامة"
    },
    # --- New Home ---
    {
        "keywords": ["new home", "house", "home", "moving", "بيت جديد", "منزل جديد"],
        "reply_en": "🏡 Celebrate new beginnings with elegant flowers perfect for welcoming a new home.",
        "reply_ar": "🏡 احتفل بالبدايات الجديدة مع زهور أنيقة مثالية لترحيب بمنزل جديد.",
        "link": "/occasion/new-home",
        "label_en": "New Home Bouquets",
        "label_ar": "باقات المنزل الجديد"
    },
    # --- Luxury / Premium ---
    {
        "keywords": ["luxury", "premium", "expensive", "rare", "exclusive", "فاخر", "مميز", "نادر"],
        "reply_en": "💎 Explore our luxury flower collection featuring premium blooms and sophisticated floral designs.",
        "reply_ar": "💎 استكشف مجموعة الزهور الفاخرة التي تضم أزهاراً متميزة وتصاميم راقية.",
        "link": "/bouquets",
        "label_en": "Luxury Collection",
        "label_ar": "المجموعة الفاخرة"
    },
    # --- Roses ---
    {
        "keywords": ["rose", "roses", "ورد", "ورود"],
        "reply_en": "🌹 Roses — the timeless symbol of beauty. We carry over 30 varieties including rare garden roses, spray roses, and our signature Black Velvet collection.",
        "reply_ar": "🌹 الورود — رمز الجمال الخالد. نحمل أكثر من 30 نوعاً من الورود النادرة وورود الحديقة وورود الرش ومجموعتنا المميزة Black Velvet.",
        "link": "/category/rose",
        "label_en": "Shop Roses",
        "label_ar": "تسوق الورود"
    },
    # --- Orchids ---
    {
        "keywords": ["orchid", "orchids", "أوركيد"],
        "reply_en": "🌺 Orchids speak of exotic elegance. Our orchid collection includes rare Phalaenopsis, Dendrobium, and Cattleya varieties — curated for the true connoisseur.",
        "reply_ar": "🌺 الأوركيد يتحدث عن الأناقة الغريبة. تشمل مجموعتنا أنواعاً نادرة من الفالاينوبسيس والديندروبيوم والكاتليا — منسقة للخبير الحقيقي.",
        "link": "/category/orchid",
        "label_en": "Shop Orchids",
        "label_ar": "تسوق الأوركيد"
    },
    # --- Tulips ---
    {
        "keywords": ["tulip", "tulips", "توليب"],
        "reply_en": "🌷 Tulips in every color of spring! Dutch, parrot, and fringe varieties — our tulip collection captures the essence of renewal and joy.",
        "reply_ar": "🌷 التوليب بكل ألوان الربيع! الأصناف الهولندية والباروت والمهدبة — مجموعة التوليب لدينا تحتوي على جوهر التجديد والبهجة.",
        "link": "/category/tulip",
        "label_en": "Shop Tulips",
        "label_ar": "تسوق التوليب"
    },
    # --- Sunflowers ---
    {
        "keywords": ["sunflower", "sunflowers", "عباد الشمس"],
        "reply_en": "🌻 Bright, bold, and cheerful! Sunflowers radiate warmth and happiness. Perfect for birthdays, get-well wishes, or simply brightening someone's day.",
        "reply_ar": "🌻 مشرقة، جريئة، ومبهجة! عباد الشمس يشع دفئاً وسعادة. مثالية لأعياد الميلاد، وتمنيات الشفاء، أو فقط لإضفاء البهجة على يوم شخص ما.",
        "link": "/category/sunflower",
        "label_en": "Shop Sunflowers",
        "label_ar": "تسوق عباد الشمس"
    },
    # --- Lilies ---
    {
        "keywords": ["lily", "lilies", "زنبق"],
        "reply_en": "🪷 Lilies — pure, elegant, and fragrant. From stargazer to calla lilies, our collection brings timeless sophistication to any occasion.",
        "reply_ar": "🪷 الزنبق — نقي، أنيق، وعطر. من زنبق ستارغيزر إلى زنبق الكالا، مجموعتنا تضفي أناقة خالدة على أي مناسبة.",
        "link": "/category/lily",
        "label_en": "Shop Lilies",
        "label_ar": "تسوق الزنبق"
    },
    # --- Budget / Affordable ---
    {
        "keywords": ["cheap", "affordable", "budget", "discount", "sale", "offer", "رخيص", "اقتصادي", "خصم", "تخفيض"],
        "reply_en": "🌼 Beauty shouldn't break the bank! Our curated everyday collection offers stunning arrangements starting from just $15 — fresh, lovely, and budget-friendly.",
        "reply_ar": "🌼 الجمال لا يجب أن يكسر البنك! مجموعتنا اليومية المنسقة تقدم ترتيبات مذهلة تبدأ من 15 دولاراً فقط — طازجة، جميلة، ومناسبة للميزانية.",
        "link": "/shop?sort=price_asc",
        "label_en": "Affordable Bouquets",
        "label_ar": "باقات اقتصادية"
    },
    # --- Custom / Bespoke ---
    {
        "keywords": ["custom", "personalized", "bespoke", "special order", "خاص", "مخصص", "تصميم خاص"],
        "reply_en": "✨ Dream it, and we'll create it. Our bespoke service lets you design a one-of-a-kind arrangement — choose your flowers, colors, and style.",
        "reply_ar": "✨ احلم بها، وسنقوم بإنشائها. خدمتنا المخصصة تتيح لك تصميم ترتيب فريد من نوعه — اختر أزهارك، ألوانك، وأسلوبك.",
        "link": "/contact",
        "label_en": "Custom Orders",
        "label_ar": "طلبات مخصصة"
    },
    # --- Delivery ---
    {
        "keywords": ["delivery", "shipping", "deliver", "ship", "توصيل", "شحن"],
        "reply_en": "🚚 We offer same-day delivery for orders placed before 2 PM. Free delivery on orders over $80.",
        "reply_ar": "🚚 نقدم توصيلاً في نفس اليوم للطلبات المقدمة قبل الساعة 2 ظهراً. توصيل مجاني للطلبات التي تزيد عن 80 دولاراً.",
        "link": "/cart",
        "label_en": "Shipping Info",
        "label_ar": "معلومات الشحن"
    },
    # --- Price / Cost ---
    {
        "keywords": ["price", "cost", "how much", "كم سعر", "سعر", "تكلفة"],
        "reply_en": "💰 Our arrangements start from $15 for everyday bouquets up to bespoke luxury designs. Browse our shop to find the perfect bouquet for your budget.",
        "reply_ar": "💰 تبدأ ترتيباتنا من 15 دولاراً للباقات اليومية وصولاً إلى التصاميم الفاخرة المخصصة. تصفح متجرنا لتجد الباقة المثالية لميزانيتك.",
        "link": "/shop",
        "label_en": "Browse Prices",
        "label_ar": "تصفح الأسعار"
    },
    # --- Contact ---
    {
        "keywords": ["contact", "call", "phone", "whatsapp", "email", "تواصل", "اتصل", "واتساب"],
        "reply_en": "📞 We'd love to hear from you! Reach us via our contact page, or chat directly with our floral consultants during business hours (9 AM – 9 PM).",
        "reply_ar": "📞 نحن نحب أن نسمع منك! تواصل معنا عبر صفحة الاتصال الخاصة بنا، أو تحدث مباشرة مع مستشارينا الزراعيين خلال ساعات العمل (9 صباحاً – 9 مساءً).",
        "link": "/contact",
        "label_en": "Contact Us",
        "label_ar": "اتصل بنا"
    },
    # --- Greetings ---
    {
        "keywords": ["hello", "hi", "hey", "good morning", "good evening", "مرحبا", "اهلا", "السلام", "صباح", "مساء"],
        "reply_en": "🌸 Welcome to Bloom Store! I'm your floral assistant. Tell me about the occasion or feeling you're shopping for, and I'll guide you to the perfect arrangement.",
        "reply_ar": "🌸 مرحباً بك في متجر Bloom! أنا مساعدك الزهري. أخبرني عن المناسبة أو الشعور الذي تشتري من أجله، وسأرشدك إلى الترتيب المثالي.",
        "link": "/shop",
        "label_en": "Browse All",
        "label_ar": "تصفح الكل"
    },
    # --- Thanks ---
    {
        "keywords": ["thank", "thanks", "shukran", "شكرا", "شكراً"],
        "reply_en": "🌺 You're most welcome! It's our pleasure to bring beauty into your world. Is there anything else I can help you with?",
        "reply_ar": "🌺 على الرحب والسعة! من دواعي سرورنا إدخال الجمال إلى عالمك. هل هناك أي شيء آخر يمكنني مساعدتك به؟",
        "link": "/shop",
        "label_en": "Continue Shopping",
        "label_ar": "مواصلة التسوق"
    },
]

# Default fallback
DEFAULT_REPLY = {
    "reply_en": "🌿 I'd love to help you find the perfect flowers! Could you tell me more about the occasion or who you're shopping for? You can also browse our full collection.",
    "reply_ar": "🌿 يسعدني مساعدتك في العثور على الزهور المثالية! هل يمكنك إخباري بالمزيد عن المناسبة أو الشخص الذي تشتري له؟ يمكنك أيضاً تصفح مجموعتنا الكاملة.",
    "link": "/shop",
    "label_en": "Browse All Flowers",
    "label_ar": "تصفح كل الزهور"
}


def find_reply(message: str) -> dict:
    """Match user message against keyword rules and return appropriate language reply."""
    msg = clean_text(message)
    is_arabic_msg = is_arabic(message)

    # Try to find matching rule
    for rule in RULES:
        for keyword in rule["keywords"]:
            if keyword in msg:
                # Return reply based on message language
                if is_arabic_msg:
                    reply = rule["reply_ar"]
                    label = rule["label_ar"]
                else:
                    reply = rule["reply_en"]
                    label = rule["label_en"]
                return {
                    "reply": reply,
                    "link": rule["link"],
                    "label": label
                }

    # No match found
    if is_arabic_msg:
        return {
            "reply": DEFAULT_REPLY["reply_ar"],
            "link": DEFAULT_REPLY["link"],
            "label": DEFAULT_REPLY["label_ar"]
        }
    else:
        return {
            "reply": DEFAULT_REPLY["reply_en"],
            "link": DEFAULT_REPLY["link"],
            "label": DEFAULT_REPLY["label_en"]
        }


@chatbot_bp.route('/', methods=['POST'])
def chat():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "Message is required"}), 400

    message = str(data['message']).strip()
    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400

    result = find_reply(message)
    return jsonify({
        "reply": result["reply"],
        "link": result["link"],
        "label": result["label"]
    }), 200