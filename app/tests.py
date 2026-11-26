"""
Testes automáticos. Para rodar:  python manage.py test

O Django cria um banco separado só para os testes e o apaga no fim, então
os dados de verdade não são tocados.

Os testes demoram um pouco de propósito: cada senha passa por 1.000.000
de repetições do PBKDF2, exatamente como no uso real.
"""

import math

from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.test import TestCase
from django.urls import reverse

from app import cifra, diceware, entropia
from app.models import Caderno, Etiqueta, Nota, NotaComum, NotaProtegida, Usuario

# Senhas usadas nos testes (todas passam pelos validadores)
SENHA_LOGIN = 'cavalo bateria grampo correto'
SENHA_ESTRESSE = 'janela tapete relogio sabonete'
SENHA_NOTA = 'girafa parafuso nuvem tijolo'


def criar_usuario(username):
    """Cria um usuário como o cadastro faz: com senha em hash e "Meu caderno"."""
    usuario = Usuario.objects.create_user(username=username, password=SENHA_LOGIN)
    usuario.criar_caderno_inicial()
    return usuario


# ----------------------------------------------------------------------
# C22: funções de segurança
# ----------------------------------------------------------------------

class CifraTests(TestCase):

    def test_cifra_e_decifra(self):
        dados = cifra.cifrar('texto secreto com acentuação', SENHA_NOTA)
        texto = cifra.decifrar(senha=SENHA_NOTA, **dados)
        self.assertEqual(texto, 'texto secreto com acentuação')

    def test_senha_errada_levanta_erro(self):
        dados = cifra.cifrar('texto secreto', SENHA_NOTA)
        with self.assertRaises(cifra.SenhaIncorreta):
            cifra.decifrar(senha='outra senha qualquer', **dados)

    def test_conteudo_alterado_levanta_erro(self):
        """A tag de autenticação do GCM denuncia qualquer byte trocado."""
        dados = cifra.cifrar('texto secreto', SENHA_NOTA)
        adulterado = bytearray(dados['conteudo_cifrado'])
        adulterado[0] ^= 1  # inverte um bit do primeiro byte
        dados['conteudo_cifrado'] = bytes(adulterado)
        with self.assertRaises(cifra.SenhaIncorreta):
            cifra.decifrar(senha=SENHA_NOTA, **dados)

    def test_salt_e_nonce_novos_a_cada_cifragem(self):
        primeiro = cifra.cifrar('mesmo texto', SENHA_NOTA)
        segundo = cifra.cifrar('mesmo texto', SENHA_NOTA)
        self.assertNotEqual(primeiro['salt'], segundo['salt'])
        self.assertNotEqual(primeiro['nonce'], segundo['nonce'])
        self.assertNotEqual(primeiro['conteudo_cifrado'], segundo['conteudo_cifrado'])

    def test_tamanhos_e_iteracoes(self):
        dados = cifra.cifrar('abc', SENHA_NOTA)
        self.assertEqual(len(dados['salt']), 16)
        self.assertEqual(len(dados['nonce']), 12)
        self.assertEqual(dados['iteracoes'], 1_000_000)
        # 3 bytes de texto + 16 bytes da tag de autenticação
        self.assertEqual(len(dados['conteudo_cifrado']), 3 + 16)

    def test_texto_original_nao_aparece_no_cifrado(self):
        dados = cifra.cifrar('palavra-reconhecivel', SENHA_NOTA)
        self.assertNotIn(b'palavra-reconhecivel', dados['conteudo_cifrado'])


class EntropiaTests(TestCase):

    def test_senha_vazia_tem_zero_bits(self):
        self.assertEqual(entropia.calcular_entropia(''), 0)

    def test_formula(self):
        # 8 letras minúsculas: 8 × log2(26)
        self.assertAlmostEqual(entropia.calcular_entropia('abcdefgh'), 8 * math.log2(26))
        # minúsculas + maiúsculas + dígitos + símbolos = 26 + 26 + 10 + 33 = 95
        self.assertAlmostEqual(entropia.calcular_entropia('aB3!'), 4 * math.log2(95))

    def test_validador_recusa_senha_fraca_e_explica(self):
        validador = entropia.ValidadorEntropia(minimo_bits=60)
        with self.assertRaises(ValidationError) as erro:
            validador.validate('abc123')
        self.assertIn('bits de entropia', erro.exception.messages[0])

    def test_validador_aceita_senha_forte(self):
        entropia.ValidadorEntropia(minimo_bits=60).validate(SENHA_LOGIN)  # não levanta erro

    def test_validador_esta_registrado_no_settings(self):
        """validate_password usa a lista AUTH_PASSWORD_VALIDATORS do settings.py."""
        with self.assertRaises(ValidationError) as erro:
            validate_password('Xk9#mQ2')  # variada, mas curta: só 46 bits
        self.assertIn('senha_pouca_entropia', [e.code for e in erro.exception.error_list])

    def test_limitacao_conhecida_senha_previsivel_passa(self):
        """
        Limitação documentada nos requisitos: a fórmula mede o formato, não
        a previsibilidade. "Senha1234!" tem 65 bits pela fórmula e passa.
        """
        self.assertGreaterEqual(entropia.calcular_entropia('Senha1234!'), 60)


class DicewareTests(TestCase):

    def test_lista_tem_7776_palavras_diferentes(self):
        lista = diceware.carregar_lista()
        self.assertEqual(len(lista), 7776)
        self.assertEqual(len(set(lista)), 7776)

    def test_gera_o_numero_de_palavras_pedido(self):
        lista = set(diceware.carregar_lista())
        for numero in range(5, 9):
            palavras = diceware.gerar_passphrase(numero).split(' ')
            self.assertEqual(len(palavras), numero)
            for palavra in palavras:
                self.assertIn(palavra, lista)

    def test_padrao_e_seis_palavras(self):
        self.assertEqual(len(diceware.gerar_passphrase().split(' ')), 6)

    def test_recusa_fora_do_intervalo(self):
        for numero in (4, 9):
            with self.assertRaises(ValueError):
                diceware.gerar_passphrase(numero)

    def test_entropia_exata(self):
        # 6 palavras × log2(7776) = 77,5 bits
        self.assertAlmostEqual(diceware.entropia_passphrase(6), 6 * math.log2(7776))
        self.assertAlmostEqual(diceware.entropia_passphrase(6), 77.5, places=1)


# ----------------------------------------------------------------------
# Contas
# ----------------------------------------------------------------------


class CadastroTests(TestCase):

    def test_cadastro_cria_meu_caderno_e_loga(self):
        resposta = self.client.post(reverse('cadastro'), {
            'username': 'ana', 'password1': SENHA_LOGIN, 'password2': SENHA_LOGIN,
        })
        self.assertRedirects(resposta, reverse('cadernos'))
        ana = Usuario.objects.get(username='ana')
        self.assertEqual([c.nome for c in ana.cadernos.all()], ['Meu caderno'])
        # A senha não fica guardada em texto: fica o hash PBKDF2.
        self.assertTrue(ana.password.startswith('pbkdf2_sha256$'))

    def test_cadastro_recusa_senha_fraca(self):
        resposta = self.client.post(reverse('cadastro'), {
            'username': 'ana', 'password1': 'abc12345', 'password2': 'abc12345',
        })
        self.assertEqual(resposta.status_code, 200)  # voltou para o formulário
        self.assertContains(resposta, 'bits de entropia')
        self.assertFalse(Usuario.objects.filter(username='ana').exists())

    def test_paginas_internas_exigem_login(self):
        resposta = self.client.get(reverse('cadernos'))
        self.assertRedirects(resposta, reverse('entrar') + '?next=/cadernos/')

    def test_ferramentas_funcionam_sem_login(self):
        self.assertEqual(self.client.get(reverse('passphrase')).status_code, 200)
        self.assertEqual(self.client.get(reverse('forca')).status_code, 200)

    def test_trocar_senha_recusa_a_senha_de_estresse(self):
        ana = criar_usuario('ana')
        ana.definir_senha_estresse(SENHA_ESTRESSE)
        ana.save()
        self.client.login(username='ana', password=SENHA_LOGIN)
        resposta = self.client.post(reverse('trocar_senha'), {
            'old_password': SENHA_LOGIN,
            'new_password1': SENHA_ESTRESSE, 'new_password2': SENHA_ESTRESSE,
        })
        self.assertEqual(resposta.status_code, 200)
        ana.refresh_from_db()
        self.assertTrue(ana.check_password(SENHA_LOGIN))  # a senha não mudou


# ----------------------------------------------------------------------
# C23: isolamento entre usuários
# ----------------------------------------------------------------------

class IsolamentoTests(TestCase):

    def setUp(self):
        self.ana = criar_usuario('ana')
        self.bia = criar_usuario('bia')
        self.caderno_ana = self.ana.cadernos.get()
        self.etiqueta_ana = Etiqueta.objects.create(dono=self.ana, nome='segredo')
        self.nota_ana = NotaComum.objects.create(
            caderno=self.caderno_ana, titulo='Nota da Ana', conteudo='só a Ana lê',
        )
        self.protegida_ana = NotaComum.objects.create(
            caderno=self.caderno_ana, titulo='Cofre da Ana', conteudo='cifrado',
        ).proteger(SENHA_NOTA)
        # Quem está logada nos testes é a Bia.
        self.client.login(username='bia', password=SENHA_LOGIN)

    def test_bia_recebe_404_nos_dados_da_ana(self):
        enderecos = [
            reverse('caderno', args=[self.caderno_ana.pk]),
            reverse('editar_caderno', args=[self.caderno_ana.pk]),
            reverse('excluir_caderno', args=[self.caderno_ana.pk]),
            reverse('editar_etiqueta', args=[self.etiqueta_ana.pk]),
            reverse('excluir_etiqueta', args=[self.etiqueta_ana.pk]),
            reverse('nota', args=[self.nota_ana.pk]),
            reverse('editar_nota', args=[self.nota_ana.pk]),
            reverse('excluir_nota', args=[self.nota_ana.pk]),
            reverse('proteger_nota', args=[self.nota_ana.pk]),
            reverse('abrir_nota', args=[self.protegida_ana.pk]),
            reverse('editar_nota_protegida', args=[self.protegida_ana.pk]),
            reverse('remover_protecao', args=[self.protegida_ana.pk]),
        ]
        for endereco in enderecos:
            self.assertEqual(self.client.get(endereco).status_code, 404, endereco)
            # 405 = a tela nem aceita POST (as de só leitura); também não altera nada.
            self.assertIn(self.client.post(endereco).status_code, (404, 405), endereco)
        # E nada da Ana foi apagado pelas tentativas.
        self.assertEqual(Nota.objects.filter(caderno__dono=self.ana).count(), 2)

    def test_bia_nao_ve_dados_da_ana_nas_listas(self):
        for nome in ('cadernos', 'etiquetas', 'busca'):
            resposta = self.client.get(reverse(nome))
            self.assertNotContains(resposta, 'Nota da Ana')
            self.assertNotContains(resposta, 'segredo')

    def test_bia_nao_cria_nota_no_caderno_da_ana(self):
        resposta = self.client.post(reverse('criar_nota'), {
            'titulo': 'Intrusa', 'conteudo': 'x', 'caderno': self.caderno_ana.pk,
        })
        self.assertEqual(resposta.status_code, 200)  # formulário recusado
        self.assertFalse(Nota.objects.filter(titulo='Intrusa').exists())

    def test_exclusao_so_acontece_por_post(self):
        self.client.login(username='ana', password=SENHA_LOGIN)
        self.client.get(reverse('excluir_nota', args=[self.nota_ana.pk]))  # só confirmação
        self.assertTrue(Nota.objects.filter(pk=self.nota_ana.pk).exists())
        self.client.post(reverse('excluir_nota', args=[self.nota_ana.pk]))
        self.assertFalse(Nota.objects.filter(pk=self.nota_ana.pk).exists())


# ----------------------------------------------------------------------
# Notas protegidas (pelas telas)
# ----------------------------------------------------------------------

class NotaProtegidaTests(TestCase):

    def setUp(self):
        self.ana = criar_usuario('ana')
        self.caderno = self.ana.cadernos.get()
        self.etiqueta = Etiqueta.objects.create(dono=self.ana, nome='banco')
        self.nota = NotaComum.objects.create(
            caderno=self.caderno, titulo='Conta', conteudo='texto original',
        )
        self.nota.etiquetas.add(self.etiqueta)
        self.client.login(username='ana', password=SENHA_LOGIN)

    def proteger(self):
        self.client.post(reverse('proteger_nota', args=[self.nota.pk]), {
            'senha': SENHA_NOTA, 'confirmacao': SENHA_NOTA,
        })
        return NotaProtegida.objects.get(pk=self.nota.pk)

    def test_proteger_tira_o_texto_do_banco_e_mantem_o_resto(self):
        protegida = self.proteger()
        self.assertFalse(NotaComum.objects.filter(pk=self.nota.pk).exists())
        self.assertEqual(protegida.titulo, 'Conta')                  # título continua legível
        self.assertEqual(list(protegida.etiquetas.all()), [self.etiqueta])
        self.assertNotIn(b'texto original', bytes(protegida.conteudo_cifrado))
        self.assertEqual(protegida.decifrar(SENHA_NOTA), 'texto original')

    def test_proteger_recusa_senha_igual_a_de_login(self):
        self.client.post(reverse('proteger_nota', args=[self.nota.pk]), {
            'senha': SENHA_LOGIN, 'confirmacao': SENHA_LOGIN,
        })
        self.assertTrue(NotaComum.objects.filter(pk=self.nota.pk).exists())

    def test_abrir_com_senha_certa_e_errada(self):
        self.proteger()
        endereco = reverse('abrir_nota', args=[self.nota.pk])
        errada = self.client.post(endereco, {'senha': 'senha errada'})
        self.assertContains(errada, 'Senha incorreta')
        self.assertNotContains(errada, 'texto original')
        certa = self.client.post(endereco, {'senha': SENHA_NOTA})
        self.assertContains(certa, 'texto original')
        # never_cache: o navegador é instruído a não guardar a página
        self.assertIn('no-store', certa['Cache-Control'])

    def test_editar_com_senha_errada_nao_altera_nada(self):
        antes = self.proteger()
        self.client.post(reverse('editar_nota_protegida', args=[self.nota.pk]), {
            'etapa': 'salvar', 'titulo': 'Trocado', 'conteudo': 'novo texto',
            'caderno': self.caderno.pk, 'senha': 'senha errada',
        })
        depois = NotaProtegida.objects.get(pk=self.nota.pk)
        self.assertEqual(depois.titulo, 'Conta')
        self.assertEqual(bytes(depois.conteudo_cifrado), bytes(antes.conteudo_cifrado))
        self.assertEqual(depois.decifrar(SENHA_NOTA), 'texto original')

    def test_editar_com_senha_certa_cifra_com_salt_e_nonce_novos(self):
        antes = self.proteger()
        self.client.post(reverse('editar_nota_protegida', args=[self.nota.pk]), {
            'etapa': 'salvar', 'titulo': 'Conta nova', 'conteudo': 'novo texto',
            'caderno': self.caderno.pk, 'senha': SENHA_NOTA,
        })
        depois = NotaProtegida.objects.get(pk=self.nota.pk)
        self.assertEqual(depois.titulo, 'Conta nova')
        self.assertEqual(depois.decifrar(SENHA_NOTA), 'novo texto')
        self.assertNotEqual(bytes(depois.salt), bytes(antes.salt))
        self.assertNotEqual(bytes(depois.nonce), bytes(antes.nonce))

    def test_remover_protecao(self):
        self.proteger()
        endereco = reverse('remover_protecao', args=[self.nota.pk])
        self.client.post(endereco, {'senha': 'senha errada'})
        self.assertTrue(NotaProtegida.objects.filter(pk=self.nota.pk).exists())
        self.client.post(endereco, {'senha': SENHA_NOTA})
        self.assertFalse(NotaProtegida.objects.filter(pk=self.nota.pk).exists())
        self.assertEqual(NotaComum.objects.get(pk=self.nota.pk).conteudo, 'texto original')

    def test_busca_nao_encontra_texto_dentro_de_nota_protegida(self):
        self.proteger()
        resposta = self.client.get(reverse('busca'), {'texto': 'original'})
        self.assertNotContains(resposta, 'Conta')
        resposta = self.client.get(reverse('busca'), {'texto': 'conta'})  # pelo título acha
        self.assertContains(resposta, 'Conta')


# ----------------------------------------------------------------------
# C24: senha de estresse
# ----------------------------------------------------------------------


class SenhaEstresseTests(TestCase):

    def setUp(self):
        self.ana = criar_usuario('ana')
        self.ana.definir_senha_estresse(SENHA_ESTRESSE)
        self.ana.save()
        caderno = Caderno.objects.create(dono=self.ana, nome='Trabalho')
        etiqueta = Etiqueta.objects.create(dono=self.ana, nome='urgente')
        nota = NotaComum.objects.create(caderno=caderno, titulo='Comum', conteudo='abc')
        nota.etiquetas.add(etiqueta)
        NotaComum.objects.create(
            caderno=caderno, titulo='Protegida', conteudo='xyz',
        ).proteger(SENHA_NOTA)
        # Dados de outra pessoa, que não podem ser afetados.
        self.bia = criar_usuario('bia')
        NotaComum.objects.create(caderno=self.bia.cadernos.get(), titulo='Da Bia', conteudo='1')

    def entrar(self, senha):
        return self.client.post(reverse('entrar'), {'username': 'ana', 'password': senha})

    def test_senha_de_estresse_fica_em_hash(self):
        self.assertTrue(self.ana.senha_estresse.startswith('pbkdf2_sha256$'))
        self.assertNotIn(SENHA_ESTRESSE, self.ana.senha_estresse)

    def test_login_normal_nao_apaga_nada(self):
        resposta = self.entrar(SENHA_LOGIN)
        self.assertRedirects(resposta, reverse('cadernos'))
        self.assertEqual(Nota.objects.filter(caderno__dono=self.ana).count(), 2)

    def test_login_com_senha_de_estresse_apaga_tudo(self):
        resposta = self.entrar(SENHA_ESTRESSE)
        # Mesmo redirecionamento do login normal: nada diferente na tela.
        self.assertRedirects(resposta, reverse('cadernos'))
        # A conta ficou igual a uma conta nova: só "Meu caderno", vazio.
        self.assertEqual([c.nome for c in self.ana.cadernos.all()], ['Meu caderno'])
        self.assertEqual(Nota.objects.filter(caderno__dono=self.ana).count(), 0)
        self.assertEqual(Etiqueta.objects.filter(dono=self.ana).count(), 0)
        # Não sobrou linha órfã nas tabelas filhas.
        self.assertEqual(NotaComum.objects.count(), 1)       # só a nota da Bia
        self.assertEqual(NotaProtegida.objects.count(), 0)
        # A tela de cadernos não mostra nenhuma mensagem.
        pagina = self.client.get(reverse('cadernos'))
        self.assertEqual(len(pagina.context['messages']), 0)

    def test_dados_de_outro_usuario_nao_sao_afetados(self):
        self.entrar(SENHA_ESTRESSE)
        self.assertTrue(Nota.objects.filter(titulo='Da Bia').exists())

    def test_senha_de_estresse_continua_valendo_depois_de_usada(self):
        self.entrar(SENHA_ESTRESSE)
        self.ana.refresh_from_db()
        self.assertTrue(self.ana.conferir_senha_estresse(SENHA_ESTRESSE))

    def test_senha_errada_nao_entra_nem_apaga(self):
        resposta = self.entrar('senha totalmente errada')
        self.assertEqual(resposta.status_code, 200)  # ficou na tela de login
        self.assertEqual(Nota.objects.filter(caderno__dono=self.ana).count(), 2)

    def test_definir_recusa_senha_igual_a_de_login(self):
        self.client.login(username='bia', password=SENHA_LOGIN)
        self.client.post(reverse('senha_estresse'), {
            'senha_estresse': SENHA_LOGIN, 'confirmacao': SENHA_LOGIN,
        })
        self.bia.refresh_from_db()
        self.assertFalse(self.bia.tem_senha_estresse())

    def test_remover_senha_de_estresse(self):
        self.client.login(username='ana', password=SENHA_LOGIN)
        self.client.post(reverse('remover_senha_estresse'))
        self.ana.refresh_from_db()
        self.assertFalse(self.ana.tem_senha_estresse())
        self.client.logout()
        # Agora a antiga senha de estresse é só uma senha errada.
        self.assertEqual(self.entrar(SENHA_ESTRESSE).status_code, 200)
        self.assertEqual(Nota.objects.filter(caderno__dono=self.ana).count(), 2)