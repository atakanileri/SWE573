"""Sample users and crafts, so the feed is not empty on a fresh database.

If the users table already has anyone in it, this does nothing. Restarting
the app will not duplicate the sample posts, and it will not change the
demo password.

The only password that is meant to be used is the demo account. By default
that is atakan@example.com / password. DEMO_EMAIL and DEMO_PASSWORD replace
those two values when they are set. They are read at startup. The default
password is a public class login, written in the README. It is not a
private secret. Do not commit a different password; set it in the
environment on the machine that runs the app.

The other people exist so the seeded posts have different authors. Their
passwords are random and not written down anywhere.
"""

import os
import secrets
from datetime import timedelta

from sqlalchemy.orm import Session as DbSession

from app.auth import hash_password
from app.models import Admin, Craft, User, utcnow

# Public class login. Tests and the README use these when the env vars are unset.
DEFAULT_DEMO_EMAIL = "atakan@example.com"
DEFAULT_DEMO_PASSWORD = "password"


def demo_email() -> str:
    """Email of the account a grader can log in with."""
    return os.environ.get("DEMO_EMAIL", "").strip() or DEFAULT_DEMO_EMAIL


def demo_password() -> str:
    """Password of that account. Blank (or unset) keeps the public default."""
    return os.environ.get("DEMO_PASSWORD", "").strip() or DEFAULT_DEMO_PASSWORD


def _person_email(sample_email: str) -> str:
    # Posts written as the default demo author follow DEMO_EMAIL, so that
    # account still owns the kilim if the email is overridden.
    if sample_email == DEFAULT_DEMO_EMAIL:
        return demo_email()
    return sample_email

# (email, display name, title, location, lat, lng, category, tags, height,
#  dimensions, colors, tools, backstory, note, description)
_SAMPLE = [
    (
        "atakan@example.com",
        "Atakan İ.",
        "Hand-woven Yörük kilim",
        "Toros, Mersin",
        36.8,
        34.0,
        "Textiles",
        ["wool", "natural-dye"],
        260,
        "120 × 180 cm",
        "Madder red, indigo, natural",
        "Vertical loom, beater comb",
        "Woven in a Yörük village using a pattern passed down from grandmother to granddaughter.",
        'The "eli belinde" motif stands for motherhood and fertility.',
        "Flat-woven wool kilim made on a vertical loom.",
    ),
    (
        "lena@example.com",
        "Lena T.",
        "Navajo two grey rug",
        "Ganado, Arizona",
        35.7,
        -109.5,
        "Textiles",
        ["wool"],
        200,
        "90 × 140 cm",
        "Grey, black, cream, red",
        "Upright loom, batten, comb",
        "The Two Grey Hills style uses mostly undyed wool from the weaver's own sheep.",
        "",
        "Woven rug in the Two Grey Hills style.",
    ),
    (
        "hemi@example.com",
        "Hemi W.",
        "Māori wood carving (whakairo)",
        "Rotorua, New Zealand",
        -38.1,
        176.2,
        "Carving",
        ["wood"],
        320,
        "40 × 25 cm",
        "Natural tōtara, paua inlay",
        "Chisels, mallet",
        "Carved panel telling the story of the carver's ancestors.",
        "Paua shell eyes represent the stars.",
        "Carved wooden panel with paua inlay.",
    ),
    (
        "selin@example.com",
        "Selin A.",
        "İznik tulip tile",
        "İznik, Bursa",
        40.4,
        29.7,
        "Pottery",
        ["clay"],
        180,
        "25 × 25 cm",
        "Cobalt blue, turquoise, coral red",
        "Brush, kiln",
        "Reproduction of a 16th-century tulip design, hand-painted under glaze.",
        "",
        "Hand-painted ceramic tile with a tulip design.",
    ),
    (
        "kana@example.com",
        "Kana S.",
        "Ainu attus robe embroidery",
        "Biratori, Hokkaido",
        42.5,
        142.1,
        "Embroidery",
        ["natural-dye"],
        290,
        "Robe, 130 cm long",
        "Indigo, white",
        "Needle, elm-bark thread",
        "Elm-bark fibre robe with protective swirl motifs at the openings.",
        "",
        "Embroidered elm-bark robe.",
    ),
    (
        "maria@example.com",
        "María G.",
        "Oaxacan black clay pot",
        "San Bartolo Coyotepec, Oaxaca",
        16.9,
        -96.7,
        "Pottery",
        ["clay"],
        230,
        "30 cm tall",
        "Black",
        "Hand shaping, quartz stone for burnishing",
        "Barro negro gets its shine from burnishing before a low-oxygen firing.",
        "",
        "Burnished black clay pot.",
    ),
    (
        "nils@example.com",
        "Nils P.",
        "Sámi duodji knife",
        "Jokkmokk, Sweden",
        66.6,
        19.8,
        "Carving",
        ["wood", "silver"],
        170,
        "22 cm",
        "Birch, reindeer antler",
        "Knife, file, engraving tool",
        "Handle of curly birch and antler with engraved patterns.",
        "",
        "Knife with a birch and antler handle.",
    ),
    (
        "naserian@example.com",
        "Naserian K.",
        "Maasai beaded collar",
        "Kajiado, Kenya",
        -1.8,
        36.8,
        "Jewelry",
        ["beads"],
        250,
        "35 cm diameter",
        "Red, blue, white, orange",
        "Needle, wire",
        "Each color carries a meaning; red stands for bravery and unity.",
        "",
        "Beaded collar.",
    ),
    (
        "ruby@example.com",
        "Ruby N.",
        "Aboriginal dot painting",
        "Papunya, Northern Territory",
        -23.2,
        131.9,
        "Painting",
        ["natural-dye"],
        300,
        "60 × 90 cm",
        "Ochre, white, black",
        "Sticks, brushes",
        "A Dreaming story about water holes on the artist's country.",
        "",
        "Dot painting in ochre.",
    ),
    (
        "kenojuak@example.com",
        "Kenojuak P.",
        "Inuit soapstone carving",
        "Cape Dorset, Nunavut",
        64.2,
        -76.5,
        "Carving",
        [],
        210,
        "18 cm tall",
        "Green-grey stone",
        "Files, saw, sandpaper",
        "A dancing bear, a common figure in Kinngait carving.",
        "",
        "Soapstone carving of a dancing bear.",
    ),
    (
        "rosa@example.com",
        "Rosa M.",
        "Shipibo-Konibo textile",
        "Ucayali, Peru",
        -8.4,
        -74.5,
        "Textiles",
        ["natural-dye"],
        270,
        "70 × 70 cm",
        "Black, cream",
        "Needle, mahogany-bark dye",
        "Kené patterns are said to be songs made visible.",
        "",
        "Textile with kené patterns.",
    ),
    (
        "juana@example.com",
        "Juana Q.",
        "Andean alpaca weaving",
        "Chinchero, Cusco",
        -13.4,
        -72.0,
        "Textiles",
        ["wool", "natural-dye"],
        190,
        "50 × 150 cm",
        "Red, green, gold",
        "Backstrap loom",
        "Dyed with cochineal and local plants, woven on a backstrap loom.",
        "",
        "Alpaca weaving made on a backstrap loom.",
    ),
    (
        "darren@example.com",
        "Darren H.",
        "Hopi kachina doll",
        "Second Mesa, Arizona",
        35.8,
        -110.5,
        "Carving",
        ["wood"],
        310,
        "30 cm tall",
        "Natural pigments",
        "Knife, rasp",
        "Carved from cottonwood root, representing a spirit being.",
        "",
        "Carved cottonwood doll.",
    ),
    (
        "moussa@example.com",
        "Moussa A.",
        "Tuareg silver cross",
        "Agadez, Niger",
        16.97,
        7.99,
        "Jewelry",
        ["silver"],
        180,
        "6 cm",
        "Silver",
        "Lost-wax casting tools",
        "Each town has its own cross design, passed from father to son.",
        "",
        "Cast silver cross.",
    ),
    (
        "eligio@example.com",
        "Eligio C.",
        "Huichol yarn painting",
        "Nayarit, Mexico",
        21.75,
        -104.9,
        "Painting",
        ["wool"],
        240,
        "40 × 40 cm",
        "Bright multicolor",
        "Beeswax board, yarn",
        "Yarn pressed into beeswax shows a deer, a sacred animal.",
        "",
        "Yarn pressed into a beeswax board.",
    ),
    (
        "aida@example.com",
        "Aida B.",
        "Kyrgyz felt shyrdak",
        "Naryn, Kyrgyzstan",
        41.4,
        76.0,
        "Textiles",
        ["wool"],
        220,
        "150 × 200 cm",
        "Red, blue",
        "Felting tools, needle",
        "Mosaic felt rug with ram's horn motifs, made by a group of women.",
        "",
        "Mosaic felt rug.",
    ),
]


def seed(db: DbSession) -> bool:
    """Insert the sample rows. Returns True only when it actually inserted them."""
    if db.query(User).first() is not None:
        return False

    now = utcnow()
    users: dict[str, User] = {}
    login_email = demo_email()
    login_password = demo_password()

    # Each person is created once. Anyone who is not the demo account gets a
    # password we throw away; those accounts only exist so posts have authors.
    for row in _SAMPLE:
        email, display_name = _person_email(row[0]), row[1]
        if email in users:
            continue
        password = login_password if email == login_email else secrets.token_urlsafe(18)
        user = User(
            email=email,
            display_name=display_name,
            password_hash=hash_password(password),
            email_verified=True,
            created_at=now - timedelta(days=2),
        )
        db.add(user)
        users[email] = user

    db.flush()

    for index, row in enumerate(_SAMPLE):
        (
            email,
            _name,
            title,
            location,
            lat,
            lng,
            category,
            tags,
            height,
            dimensions,
            colors,
            tools,
            backstory,
            note,
            description,
        ) = row
        db.add(
            Craft(
                author_id=users[_person_email(email)].id,
                title=title,
                description=description,
                image_url="",
                category=category,
                tags=tags,
                dimensions=dimensions,
                colors=colors,
                tools=tools,
                backstory=backstory,
                note=note,
                location_text=location,
                latitude=lat,
                longitude=lng,
                status="published",
                card_height=height,
                # Newest first in the feed. The kilim is the first sample, so
                # it lands at the top-left of the masonry grid, like the mockup.
                # A post created during the demo is newer than all of these.
                created_at=now - timedelta(hours=index + 1),
            )
        )

    db.commit()
    return True


def ensure_demo_admin(db: DbSession) -> None:
    """The demo account is the admin.

    seed() does nothing once any user exists, and the deployed database
    already has users. This still runs on every startup. Admin is its own
    table because create_all will create a missing table, and it will not
    add a column to users.
    """
    email = demo_email()
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None:
        return
    already = db.query(Admin.id).filter(Admin.user_id == user.id).first()
    if already is not None:
        return
    db.add(Admin(user_id=user.id))
    db.commit()
