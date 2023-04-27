# UnidSisgp
Aplicativo desenvolvido em Python para a gestão do PGD em cada unidade.

Este aplicativo utiliza o banco de dados do SISGP (SUSEP), o que permite seu uso concomitante a este sistema.

Além da gestão individual dos planos de trablho, as pessoas alocadas na unidade possam ver os planos umas das outras. 

Das suas características, destacam-se não haver fase de candidatura, não haver envio de e-mails, algumas ações podem ser 
realizadas em lote e objetos e assuntos podem ser relacionados às atividades dos planos de trabalho de cada pessoa.

Como este sistema registra o log dos commits realizados, é necessário uma tabela no DBSISGP. Abaixo seguem as instruções SQL para tal:

      USE [DBSISGP]   
      GO

      /****** Object:  Table [Apoio].[log_unid]  ******/
      SET ANSI_NULLS ON
      GO

      SET QUOTED_IDENTIFIER ON
      GO

      CREATE TABLE [Apoio].[log_unid](
            [id] [bigint] IDENTITY(1,1) NOT NULL,
            [data_hora] [datetime] NOT NULL,
            [user_id] [bigint] NOT NULL,
            [msg] [varchar](150) NOT NULL,
      CONSTRAINT [PK_log_unid] PRIMARY KEY CLUSTERED 
      (
            [id] ASC
      )WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
      ) ON [PRIMARY]
      GO

Caso não exista, é necessário criar previamente o schema Apoio.

O acesso se vale do DIT do LDAP da instituição. Em resumo, o sistema pega as credenciais do usuário e, com elas, se conecta no servidor LDAP. Caso o usuário exista no DIT,
o sistema verifica se o e-mail cadastrado na tabela Pessoas do DBSISGP corresponde ao e-mail cadastrado no DIT. Confirmando, o acesso é fornecido.

Existem 4 usuárois de teste: Chefe_1, Chefe_2, Pessoa_1, Pessoa_2. Caso estes existam na tabela Pessoas (campo pesNome), o sistema permite o login sem consulta ao LDAP. 
Recomenda-se então usar somente  no ambiente de testes/homologação.

O código está preparado para ter sua imagem docker gerada (portas 5002:5002), sendo necessárias as seguintes variáveis de ambiente:

      DB_SERVER: nome do servidor onde reside o banco de dados
      DB_PORT: número da porta de acesso ao banco de dados
      DB_DATABASE: nome do bando de dados, geralmente "DBSISGP"
      DB_USER: nome do usuário de acesso ao banco de dados
      DB_PWD: senha do usuário de acesso ao banco de dados
      LDAP_URL: url do servidor do LDAP, com  a informação da porta usada, exemplo: "ldap.xxx.xx:1234"
      STR_CONEXAO: string de para conexão com o LDAP, exemplo: "ou=People,dc=xxxx,dc=xx"
      STR_SEARCH: string de procura no DIT do LDAP, exemplo "dc=xxxx,dc=xx"
      STR_ATRIBUTO: este sistema só usa o artibuto de e-mail, por exemplo: "mail"
      CONDIC: se informada com o valor "chefe_nao_pode_remoto", indica ao sistema que nenhuma pessoa com função pode realizar teletrabalho integral. Caso contrário, informar "".

Ao gerar sua própria imagem, recomenda-se alterar no arquivo flask.cfg a SECRECT_KEY do sistema, ou torne ela uma variável de sistema, se preferir.      

...
