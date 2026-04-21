import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import datetime

# --- CONFIGURACIÓN CRÍTICA (CAMBIA ESTO) ---
TOKEN = 'MTQ5NTk4MjI3NzgwNzgzNzE5NA.GJ3Pdc.1w7DSSNrtMf8Tmqmwdox2i5WDCdgQC_DOgG65E'
ID_CATEGORIA_TICKETS = 1474872249625481327  # ID de la categoría donde se abrirán los tickets
ID_ROL_STAFF = 1449516428645630092       # ID del rol de Staff (Moderador/Admin)
ID_CANAL_LOGS = 1449500331414393009      # ID del canal privado donde se verán las acciones
URL_LOGO = 'https://cdn.discordapp.com/attachments/1458860581787537802/1495980006126653490/descarga_14.jfif?ex=69e83773&is=69e6e5f3&hm=e7108df517f5dadaa6ccc6be146450be19a58bce1dfd68c5e34d36db5da5e9b3'
# ------------------------------------------

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- CLASE: MODAL DE CIERRE (Pide la Razón) ---
class CloseTicketModal(Modal):
    def __init__(self, channel):
        super().__init__(title="Cerrar Ticket | NX Gen Store")
        self.channel = channel
        self.reason_input = TextInput(
            label="Razón del Cierre",
            style=discord.TextStyle.paragraph,
            placeholder="Ej: Venta completada, Usuario no responde...",
            required=True,
            min_length=5,
            max_length=200
        )
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        # 1. Avisar que se está cerrando
        await interaction.response.send_message("🚧 Cerrando ticket y generando logs...", ephemeral=True)
        
        # 2. Generar Log
        logs_channel = bot.get_channel(ID_CANAL_LOGS)
        ticket_owner_id = int(self.channel.name.split('-')[-1]) # Asumiendo formato tipo-nombre-id
        ticket_owner = bot.get_user(ticket_owner_id) or "Usuario Desconocido"

        embed_log = discord.Embed(
            title="🔒 Ticket Cerrado",
            color=0xFF0000, # Rojo Puro
            timestamp=datetime.datetime.now()
        )
        embed_log.set_author(name="NX Gen Store Logs", icon_url=URL_LOGO)
        embed_log.add_field(name="Ticket:", value=self.channel.mention, inline=False)
        embed_log.add_field(name="Abierto por:", value=getattr(ticket_owner, "mention", "Desconocido"), inline=True)
        embed_log.add_field(name="Cerrado por:", value=interaction.user.mention, inline=True)
        embed_log.add_field(name="Razón:", value=self.reason_input.value, inline=False)
        embed_log.set_footer(text=f"ID: {self.channel.id}")

        await logs_channel.send(embed=embed_log)

        # 3. Borrar el canal
        await self.channel.delete(reason=f"Cerrado por {interaction.user}: {self.reason_input.value}")


# --- CLASE: BOTONES DENTRO DEL TICKET ---
class TicketActionView(View):
    def __init__(self, channel):
        super().__init__(timeout=None)
        self.channel = channel

    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket", emoji="🔒")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Solo el Staff puede cerrar (o Admin)
        if interaction.user.guild_permissions.administrator or ID_ROL_STAFF in [role.id for role in interaction.user.roles]:
            await interaction.response.send_modal(CloseTicketModal(self.channel))
        else:
            await interaction.response.send_message("❌ Solo el Staff puede cerrar este ticket.", ephemeral=True)


# --- CLASE: PANEL PRINCIPAL (Creación de Tickets) ---
class TicketPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def create_ticket(self, interaction, tipo_emoji, tipo_nombre):
        guild = interaction.guild
        categoria = guild.get_channel(ID_CATEGORIA_TICKETS)
        rol_staff = guild.get_role(ID_ROL_STAFF)
        
        if not categoria or not rol_staff:
            return await interaction.response.send_message("❌ Error: Categoría o Rol de Staff no configurados.", ephemeral=True)

        # Permisos estrictos
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
            rol_staff: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        # Crear canal con ID del usuario para logs fáciles
        channel_name = f"{tipo_nombre.lower()}-{interaction.user.name}-{interaction.user.id}"
        channel = await guild.create_text_channel(
            name=channel_name,
            category=categoria,
            overwrites=overwrites,
            topic=f"Ticket de {tipo_nombre} para {interaction.user} (ID: {interaction.user.id})"
        )

        # Embed chulo DENTRO del ticket
        embed_welcome = discord.Embed(
            title=f"{tipo_emoji} Ticket de {tipo_nombre}",
            description=f"Hola {interaction.user.mention},\nGracias por contactar a **NX Gen Store**.\n\n"
                        "Un miembro de nuestro Staff te atenderá lo antes posible.\n\n"
                        "**Mientras esperas:**\n"
                        "- Describe tu consulta con detalles.\n"
                        "- Si es una compra, dinos qué producto quieres.\n"
                        "- Si es soporte, explica el problema.",
            color=0xFF0000 # Rojo Puro
        )
        embed_welcome.set_thumbnail(url=URL_LOGO)
        embed_welcome.set_footer(text="Usa el botón de abajo para cerrar el ticket (Solo Staff).")

        # Enviar mensaje con el botón de CERRAR
        await channel.send(embed=embed_welcome, view=TicketActionView(channel))
        await interaction.response.send_message(f"✅ Tu ticket ha sido creado en {channel.mention}", ephemeral=True)


    @discord.ui.button(label="Buy / Comprar", style=discord.ButtonStyle.green, custom_id="btn_buy", emoji="💰", row=0)
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "💰", "Buy")

    @discord.ui.button(label="Support / Soporte", style=discord.ButtonStyle.blurple, custom_id="btn_support", emoji="🛠️", row=0)
    async def support_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "🛠️", "Support")

    @discord.ui.button(label="Partner", style=discord.ButtonStyle.gray, custom_id="btn_partner", emoji="🤝", row=1)
    async def partner_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "🤝", "Partner")

    @discord.ui.button(label="Others / Otros", style=discord.ButtonStyle.red, custom_id="btn_others", emoji="📩", row=1)
    async def others_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "📩", "Others")


# --- COMANDOS Y EVENTOS ---
@bot.event
async def on_ready():
    print(f'✅ NX GenBot Online como {bot.user}')
    # Esto asegura que los botones funcionen incluso si el bot se reinicia
    bot.add_view(TicketPanelView())
    await bot.change_presence(activity=discord.Game(name="NX Gen Store | !setup"))

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_tickets(ctx):
    """Comando para lanzar el panel principal"""
    embed_panel = discord.Embed(
        title="✨ Centro de Soporte | NX Gen Store",
        description="Bienvenido al sistema de atención al cliente.\n"
                    "Por favor, presiona el botón que mejor describa tu consulta:\n\n"
                    "💰 **Buy:** Adquisición de productos y servicios.\n"
                    "🛠️ **Support:** Ayuda técnica, dudas o reclamos.\n"
                    "🤝 **Partner:** Alianzas, colaboraciones y media.\n"
                    "📩 **Others:** Cualquier otro asunto no listado.",
        color=0xFF0000 # Rojo Puro
    )
    embed_panel.set_author(name="NX Gen Store", icon_url=URL_LOGO)
    embed_panel.set_image(url=URL_LOGO) # Ponemos el logo grande abajo para estructurar
    embed_panel.set_footer(text="Atención 24/7 | NX Gen Store")
    
    await ctx.send(embed=embed_panel, view=TicketPanelView())
    await ctx.message.delete() # Borra el comando !setup_tickets

bot.run(TOKEN)
