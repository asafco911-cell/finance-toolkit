#with open("notes.txt", "w") as file:
 #   file.write("First line\n")
  #  file.write("Second line\n")


with open("notes.txt", "r") as file:
    content = file.read()
    print(content)

#with open("notes.txt", "a") as file:      # ✅ "a" = מוסיף בסוף, לא מוחק
 #   file.write("New line from code\n")

with open("notes.txt", "r") as file:
    content = file.read()
    print(content)
    


