from escpos.printer import Usb

# Replace with your actual USB IDs
p = Usb(0x0483, 0x070b)

# Decorative Flower Border (ASCII style)
border = "* * * * * * * * * * * * * * * * *\n"

# Print top flower border
p.set(align='center')
p.text(border)

# Add some spacing before name
p.text("\n\n")

# Print the name "Yasish" in the center with bold and enlarged text
p.set(align='center', bold=True, width=2, height=2)
p.text("YASISH\n")

# Add some spacing after name
p.text("\n\n")

# Print bottom flower border
p.set(align='center')
p.text(border)

# Footer or empty space for tear
p.text("\n\n\n")

# Cut paper
p.cut()
