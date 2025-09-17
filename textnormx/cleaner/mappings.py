# Tables of replacements “safe” extendable.
PUA_BULLETS = {
    "\uf0b7", "\uf06e", "\uf0a7", "\uf0d8", "\uf0fc",  # most frequent
}
# Remplacement 1→1 
TRANSLATE_MAP = {
    # Bullets & ponctuation
    "•": "•", "·": "•", "‧": "•", "∙": "•",
    # typographiques → ASCII
    "“": '"', "”": '"', "‟": '"', "„": '"', "’": "'", "‘": "'", "‚": "'",
    #  '-'
    "–": "-", "—": "-",
    # NBSP → space
    "\u00A0": " ",
}
