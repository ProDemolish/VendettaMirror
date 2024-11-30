import discord
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_fixed
import os
import asyncio

# Ładowanie tokenu z pliku token_mirror.env
load_dotenv('token_mirror.env')
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Konfiguracja Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
creds = None
sheet = None
achievements_sheet = None
achievements_definitions_sheet = None
try:
    creds = ServiceAccountCredentials.from_json_keyfile_name('discordbot.json', scope)
    client_gs = gspread.authorize(creds)
    sheet = client_gs.open("Vouch Data").sheet1
    achievements_sheet = client_gs.open("Vouch Data").worksheet("Achievements")
    achievements_definitions_sheet = client_gs.open("Vouch Data").worksheet("Achievements Definition")
    print("Połączono z Google Sheets.")
except Exception as e:
    print(f"Błąd podczas połączenia z Google Sheets: {e}")

# Konfiguracja bota z komendami
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True  # Aby mieć dostęp do informacji o użytkownikach na serwerze

bot = commands.Bot(command_prefix="?", intents=intents)
request_queue = asyncio.Queue()

# Definicja kategorii pochwał
categories = {
    "boosting": "Boosting Pochwały",
    "crafting": "Crafting Pochwały",
    "carry": "Carry Pochwały",
    "tutor": "Tutor Pochwały",
    "buildfixer": "Buildfixer Pochwały"
}

# Definicja rang i progów
ranks = {
    "Newbie": 0,
    "Newcomer": 50,
    "Junior Member": 105,
    "Apprentice": 165,
    "Initiate": 230,
    "Associate": 300,
    "Adept": 375,
    "Journeyman": 455,
    "Senior Member": 540,
    "Specialist": 630,
    "Expert": 725,
    "Mentor": 825,
    "Champion": 930,
    "Guardian": 1040,
    "Elite": 1155,
    "Master": 1275,
    "Grandmaster": 1400,
    "Advisor": 1530,
    "Architect": 1665,
    "Visionary": 1805,
    "Legend": 1950
}

def get_user_rank(total_vouches):
    for rank, min_vouches in reversed(ranks.items()):
        if total_vouches >= min_vouches:
            return rank
    return "Newbie"

def vouches_to_next_rank(total_vouches):
    for rank, min_vouches in ranks.items():
        if total_vouches < min_vouches:
            return min_vouches - total_vouches
    return 0

@bot.event
async def setup_hook():
    try:
        # Synchronizacja komend slash z serwerem
        await bot.tree.sync()
        print("Komendy zostały zsynchronizowane.")
    except Exception as e:
        print(f"Błąd podczas synchronizacji komend: {e}")

@bot.event
async def on_ready():
    print(f'Bot VendettaMirror ({bot.user}) has connected to Discord!')
    bot.loop.create_task(handle_requests())

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def update_google_sheets(user_id, category):
    global sheet
    # Funkcja do aktualizacji Google Sheets z ponawianiem próby
    if sheet is None:
        raise ValueError("Google Sheet is not initialized.")
    user_id = str(user_id)
    cell = sheet.find(user_id)
    category_column = categories[category.lower()]
    if cell:
        current_vouch = int(sheet.cell(cell.row, sheet.find(category_column).col).value or 0)
        sheet.update_cell(cell.row, sheet.find(category_column).col, current_vouch + 1)
    else:
        member = bot.get_guild(interaction.guild_id).get_member(int(user_id))
        new_row = [user_id, member.display_name] + [0] * len(categories)
        new_row[list(categories.keys()).index(category.lower()) + 2] = 1
        sheet.append_row(new_row)

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def update_achievements(user_id, achievement):
    global achievements_sheet
    if achievements_sheet is None:
        raise ValueError("Achievements Sheet is not initialized.")
    user_id = str(user_id)  # Upewnienie się, że user_id jest typu str
    cell = achievements_sheet.find(user_id)
    if cell:
        current_achievements = achievements_sheet.cell(cell.row, 3).value or ""
        if achievement not in current_achievements:
            updated_achievements = current_achievements + f", {achievement}" if current_achievements else achievement
            achievements_sheet.update_cell(cell.row, 3, updated_achievements)
    else:
        member = bot.get_guild(interaction.guild_id).get_member(int(user_id))
        new_row = [user_id, member.display_name, achievement]
        achievements_sheet.append_row(new_row)

async def handle_requests():
    while True:
        interaction, args = await request_queue.get()
        try:
            update_google_sheets(*args)
            await interaction.followup.send(f"Pomyślnie dodano pochwałę dla użytkownika {interaction.guild.get_member(args[0]).display_name} w kategorii {args[1]}!")
        except Exception as e:
            await interaction.followup.send(f"Wystąpił błąd podczas przetwarzania pochwały: {e}")

@bot.tree.command(name="vouch", description="Dodaj pochwałę dla użytkownika w określonej kategorii.")
@app_commands.describe(member="Użytkownik, który otrzymuje pochwałę", category="Kategoria pochwały (boosting, crafting, carry, tutor, buildfixer)")
async def vouch(interaction: discord.Interaction, member: discord.Member, category: str):
    await interaction.response.defer(thinking=True)
    try:
        update_google_sheets(member.id, category)
        await interaction.followup.send(f"Pomyślnie dodano pochwałę dla użytkownika {member.display_name} w kategorii {category}!")
    except Exception as e:
        await interaction.followup.send(f"Wystąpił błąd podczas dodawania pochwały: {e}")

@bot.tree.command(name="give_achievement", description="Dodaj osiągnięcie użytkownikowi (dostępne tylko dla administratora).")
@app_commands.describe(member="Użytkownik, który otrzymuje osiągnięcie", achievement="Nazwa osiągnięcia")
async def give_achievement(interaction: discord.Interaction, member: discord.Member, achievement: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Nie masz uprawnień do używania tej komendy.", ephemeral=True)
        return
    try:
        # Sprawdzenie, czy osiągnięcie istnieje w "Achievements Definition"
        existing_achievement = achievements_definitions_sheet.findall(achievement)
        if not existing_achievement:
            await interaction.response.send_message(f"Proszę utworzyć takie osiągnięcie, ponieważ nie ma go na liście.", ephemeral=True)
            return
        update_achievements(member.id, achievement)
        await interaction.response.send_message(f"Pomyślnie dodano osiągnięcie '{achievement}' dla użytkownika {member.name}.")
    except Exception as e:
        await interaction.response.send_message(f"Wystąpił błąd podczas dodawania osiągnięcia: {e}")

@bot.tree.command(name="create_achievement", description="Stwórz nowe osiągnięcie (dostępne tylko dla administratora).")
@app_commands.describe(name="Nazwa osiągnięcia", description="Opis osiągnięcia")
async def create_achievement(interaction: discord.Interaction, name: str, description: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Nie masz uprawnień do używania tej komendy.", ephemeral=True)
        return
    try:
        # Sprawdzenie, czy osiągnięcie już istnieje
        existing_achievement = achievements_definitions_sheet.findall(name)
        if existing_achievement:
            await interaction.response.send_message(f"Osiągnięcie '{name}' już istnieje.", ephemeral=True)
            return

        # Dodanie nowego osiągnięcia do arkusza "Achievements Definition"
        achievements_definitions_sheet.append_row([name, description])
        await interaction.response.send_message(f"Osiągnięcie '{name}' zostało stworzone.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Wystąpił błąd podczas tworzenia osiągnięcia: {e}", ephemeral=True)

# Komenda slash "list_achievements" do wyświetlania wszystkich osiągnięć w formie osadzonej (Embed)
@bot.tree.command(name="list_achievements", description="Wyświetl listę wszystkich osiągnięć (dostępne tylko dla administratora).")
async def list_achievements(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Nie masz uprawnień do używania tej komendy.", ephemeral=True)
        return
    try:
        all_achievements = achievements_definitions_sheet.get_all_records()
        embed = discord.Embed(title="Lista osiągnięć", color=discord.Color.gold())
        for achievement in all_achievements:
            embed.add_field(name=achievement['name'], value=achievement['description'], inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Wystąpił błąd podczas pobierania listy osiągnięć: {e}", ephemeral=True)

@bot.tree.command(name="vouch_count", description="Sprawdź liczbę pochwał użytkownika we wszystkich kategoriach oraz jego rangę i osiągnięcia.")
async def vouch_count(interaction: discord.Interaction, member: discord.Member = None):
    await interaction.response.defer(thinking=True)
    if sheet is None or achievements_sheet is None:
        await interaction.followup.send("Błąd: Google Sheet nie jest zainicjalizowany.")
        return
    if member is None:
        member = interaction.user

    user_id = str(member.id)
    try:
        cell = sheet.find(user_id)
        if cell:
            embed = discord.Embed(title=f"Pochwały użytkownika {member.name}", color=discord.Color.green())
            total_vouches = 0
            for cat_key, cat_name in categories.items():
                vouch_count = int(sheet.cell(cell.row, sheet.find(cat_name).col).value or 0)
                total_vouches += vouch_count
                embed.add_field(name=f"{cat_key.capitalize()} Pochwały", value=str(vouch_count), inline=False)
            user_rank = get_user_rank(total_vouches)
            next_rank_vouches = vouches_to_next_rank(total_vouches)
            embed.add_field(name="Łącznie pochwał", value=str(total_vouches), inline=False)
            embed.add_field(name="Ranga", value=user_rank, inline=False)
            if next_rank_vouches > 0:
                embed.add_field(name="Pochwały do następnej rangi", value=str(next_rank_vouches), inline=False)

            # Dodanie osiągnięć
            achievements_cell = achievements_sheet.find(user_id)
            if achievements_cell:
                achievements = achievements_sheet.cell(achievements_cell.row, 3).value or "Brak osiągnięć"
                embed.add_field(name="Osiągnięcia", value=achievements, inline=False)
            else:
                embed.add_field(name="Osiągnięcia", value="Brak osiągnięć", inline=False)

            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"{member.name} nie ma jeszcze żadnych pochwał.")
    except Exception as e:
        await interaction.followup.send(f"Wystąpił błąd podczas sprawdzania pochwał: {e}")

@bot.tree.command(name="vouch_rank")
async def vouch_rank(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    if sheet is None or achievements_sheet is None:
        await interaction.followup.send("Błąd: Google Sheet nie jest zainicjalizowany.")
        return
    try:
        all_data = sheet.get_all_records()
        all_data.sort(key=lambda x: sum(int(x.get(cat, 0) or 0) for cat in categories.values()), reverse=True)
        embed = discord.Embed(title="TOP 20 Ranking Pochwał", color=discord.Color.blue())
        for i, record in enumerate(all_data[:20], start=1):
            total_vouches = sum(int(record.get(cat, 0) or 0) for cat in categories.values())
            user_rank = get_user_rank(total_vouches)
            user_id = str(record['User ID'])
            achievements_cell = achievements_sheet.find(user_id)
            achievements = achievements_sheet.cell(achievements_cell.row, 3).value if achievements_cell else "Brak osiągnięć"
            embed.add_field(name=f"{i}. {record['Username']}", value=f"Łącznie pochwał: {total_vouches}, Ranga: {user_rank}, Osiągnięcia: {achievements}", inline=False)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Wystąpił błąd podczas pobierania rankingu: {e}")

# Uruchomienie bota
try:
    bot.run(TOKEN)
except Exception as e:
    print(f"Błąd podczas uruchamiania bota: {e}")
