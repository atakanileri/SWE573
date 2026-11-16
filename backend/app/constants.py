"""Official lists the prototype lets people pick from.

The requirements say tags and categories should come from a list an admin
controls. There is no admin screen yet, so the lists live here. Adding a new
one means editing this file and restarting.
"""

CATEGORIES = [
    "Textiles",
    "Pottery",
    "Carving",
    "Jewelry",
    "Painting",
    "Embroidery",
]

TAGS = [
    "wool",
    "natural-dye",
    "clay",
    "wood",
    "beads",
    "silver",
]

# The interactive mockup uses these two labels. Kept here so the form and the
# API agree on the wording.
REPORT_REASONS = [
    "Wrong or misleading information",
    "Not an indigenous craft",
    "Offensive or disrespectful content",
    "Copyright / not the poster's work",
    "Other",
]
