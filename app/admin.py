from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from app.models import Caderno, Etiqueta, Nota, NotaComum, NotaProtegida, Usuario



class NotaComumInline(admin.TabularInline):
    """Notas comuns dentro do caderno. O administrador pode criar por aqui."""
    model = NotaComum
    fk_name = 'caderno'       # a chave estrangeira que liga a nota ao caderno
    fields = ['titulo', 'conteudo']
    extra = 1                 # uma linha em branco para criar nota nova
    show_change_link = True


class NotaProtegidaInline(admin.TabularInline):
    """Notas protegidas dentro do caderno: somente leitura e sem criar."""
    model = NotaProtegida
    fk_name = 'caderno'
    fields = ['titulo', 'iteracoes', 'criada_em']
    readonly_fields = ['titulo', 'iteracoes', 'criada_em']
    extra = 0

    def has_add_permission(self, request, obj=None):
        # Criar uma nota protegida exige a senha, e o painel não cifra nada.
        return False

    def has_change_permission(self, request, obj=None):
        return False


class EtiquetaInline(admin.TabularInline):
    """
    Etiquetas dentro da nota. Numa relação N:N o Django cria uma tabela
    intermediária escondida (Nota.etiquetas.through), e é ela que o inline edita.
    """
    model = Nota.etiquetas.through
    extra = 1
    verbose_name = 'Etiqueta da nota'
    verbose_name_plural = 'Etiquetas da nota'


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """
    Usa a tela de usuários pronta do Django (UserAdmin). O campo
    senha_estresse fica de fora de propósito: ninguém precisa ver esse hash.
    A criação de usuário por aqui também passa pelos validadores de senha.
    """
    list_display = ['username', 'email', 'is_staff', 'is_active', 'date_joined']
    search_fields = ['username', 'email']


@admin.register(Caderno)
class CadernoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'dono', 'criado_em']
    search_fields = ['nome', 'dono__username']
    list_filter = ['dono']
    inlines = [NotaComumInline, NotaProtegidaInline]


@admin.register(Etiqueta)
class EtiquetaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'dono']
    search_fields = ['nome', 'dono__username']
    list_filter = ['dono']


@admin.register(NotaComum)
class NotaComumAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'caderno', 'criada_em', 'atualizada_em']
    search_fields = ['titulo', 'conteudo', 'caderno__nome']
    list_filter = ['caderno__dono']
    exclude = ['etiquetas']   # as etiquetas são editadas pelo inline
    inlines = [EtiquetaInline]


@admin.register(NotaProtegida)
class NotaProtegidaAdmin(admin.ModelAdmin):
    """
    Nota protegida no painel: dá para ver título, datas e o TAMANHO dos
    dados cifrados, mas não o conteúdo. Não pode ser criada por aqui.
    """
    list_display = ['titulo', 'caderno', 'criada_em', 'atualizada_em']
    search_fields = ['titulo', 'caderno__nome']   # sem busca no conteúdo: está cifrado
    list_filter = ['caderno__dono']
    exclude = ['etiquetas']
    readonly_fields = [
        'tamanho_conteudo_cifrado', 'tamanho_salt', 'tamanho_nonce',
        'iteracoes', 'criada_em', 'atualizada_em',
    ]
    inlines = [EtiquetaInline]

    def has_add_permission(self, request):
        return False

    # Os campos binários aparecem só como tamanho em bytes.
    @admin.display(description='Conteúdo cifrado')
    def tamanho_conteudo_cifrado(self, nota):
        return f'{len(bytes(nota.conteudo_cifrado))} bytes (cifrado com AES-256-GCM)'

    @admin.display(description='Salt')
    def tamanho_salt(self, nota):
        return f'{len(bytes(nota.salt))} bytes'

    @admin.display(description='Nonce')
    def tamanho_nonce(self, nota):
        return f'{len(bytes(nota.nonce))} bytes'
