-- Seed: ONGs_v2 (33 novas ONGs)
-- Duplicatas excluídas: Ação da Cidadania, Gerando Falcões (já existem no banco)
-- Gerado em: 2026-02-28
--
-- Correções aplicadas no CSV de origem:
--   1. 29 linhas com URL deslocada de donation_url → bank_info: campo corrigido
--   2. Cáritas: CNPJ caiu em email e banco em pix_key (faltou vírgula no CSV)
--   3. CUFA: banco em pix_key → movido para bank_info
--   4. GRAD: categoria 'Causa Animal' → padronizado para 'Animais'
--   5. state: nomes por extenso convertidos para código UF de 2 chars
--   6. city: campos vazios mantidos como '' (NOT NULL permite string vazia)

INSERT INTO ongs (id, name, category, subcategory, city, state, phone, website, email, pix_key, bank_info, donation_url, is_active)
VALUES
  (gen_random_uuid(), 'Amigos do Bem', 'Fome', 'Desenvolvimento do Sertão Nordestino', 'São Paulo', 'SP', '(11) 3019-0107', 'amigosdobem.org', 'informacoes@amigosdobem.org', '', '', 'https://benfeitoria.com/pagamento/amigosdobempqd/tipo', true),
  (gen_random_uuid(), 'Casa Miga', 'LGBTQIA+', 'Acolhimento de Refugiados e Vulneráveis', 'Manaus', 'AM', '', '', '', '', '', 'https://www.paraquemdoar.com.br/busca', true),
  (gen_random_uuid(), 'Coletivo Feminista Sexualidade e Saúde', 'Mulheres', 'Saúde das Mulheres e Perspectiva Feminista', 'São Paulo', 'SP', '', '', '', '', '', 'https://www.paraquemdoar.com.br/busca', true),
  (gen_random_uuid(), 'Instituto Madeira da Terra', 'Mulheres', 'Igualdade de Gênero no Sertão', '', 'CE', '', '', '', '', '', 'https://www.paraquemdoar.com.br/busca', true),
  (gen_random_uuid(), 'Obras Sociais Missionários da Compaixão', 'Fome', 'Assistência em Comunidades Periféricas', 'Salvador', 'BA', '', '', '', '', '', 'https://www.paraquemdoar.com.br/busca', true),
  (gen_random_uuid(), 'CEPFS', 'Fome', 'Desenvolvimento Rural Sustentável', 'Teixeira', 'PB', '', 'cepfs.org.br', '', '24226128000136', 'Bradesco Ag: 1563-6 CC: 17651-6', 'https://www.paraquemdoar.com.br/cepfs', true),
  (gen_random_uuid(), 'Associação Vaga Lume', 'Educação', 'Leitura em Comunidades Rurais', '', 'AM', '', 'vagalume.org.br', '', '', '', 'https://www.paraquemdoar.com.br/busca', true),
  (gen_random_uuid(), 'Instituto Acaia', 'Educação', 'Educação por meio da Arte', '', 'MS', '', 'acaia.org.br', '', '', '', 'https://www.paraquemdoar.com.br/busca', true),
  (gen_random_uuid(), 'Pipa', 'Educação', 'Justiça Social e Brincar', '', 'SP', '', '', '', '', '', 'https://www.paraquemdoar.com.br/busca', true),
  (gen_random_uuid(), 'Instituto Paulo Gontijo', 'Saúde', 'Apoio a Pacientes com ELA', 'São Paulo', 'SP', '', 'ipg.org.br', '', '', '', 'https://www.paraquemdoar.com.br/busca', true),
  (gen_random_uuid(), 'Instituto Nosso Olhar', 'Pessoas com Deficiência', 'Inclusão de Pessoas com Síndrome de Down', 'São Paulo', 'SP', '', 'noscoolhar.org.br', '', '', '', 'https://www.paraquemdoar.com.br/busca', true),
  (gen_random_uuid(), 'Cáritas Arquidiocesana Olinda e Recife', 'Emergências', 'Auxílio a Vítimas de Enchentes', 'Recife', 'PE', '', '', '', '29420681000129', 'BB Ag: 5740-1 CC: 60.691-0', 'https://www.paraquemdoar.com.br/blog/chuvas-em-pernambuco', true),
  (gen_random_uuid(), 'CUFA Pernambuco', 'Emergências', 'Arrecadação de Mantimentos em Favelas', 'Recife', 'PE', '', '', '', '', 'Ag: 0001 CC: 56883499-8', 'https://www.paraquemdoar.com.br/blog/chuvas-em-pernambuco', true),
  (gen_random_uuid(), 'GoodTruck Brasil', 'Fome', 'Logística Reversa de Alimentos', 'Curitiba', 'PR', '', 'goodtruck.org.br', '', '', '', 'https://www.paraquemdoar.com.br/hub/fome', true),
  (gen_random_uuid(), 'Pará Solidário', 'Fome', 'Assistência a Comunidades Carentes', 'Belém', 'PA', '', '', '', '', '', 'https://www.paraquemdoar.com.br/hub/fome', true),
  (gen_random_uuid(), 'Misturaí', 'Fome', 'Geração de Renda e Educação', 'Porto Alegre', 'RS', '', 'misturai.org', '', '', '', 'https://www.paraquemdoar.com.br/hub/fome', true),
  (gen_random_uuid(), 'G10 das Favelas', 'Fome', 'Segurança Alimentar em Favelas', 'São Paulo', 'SP', '', 'g10favelas.org.br', '', '', '', 'https://www.paraquemdoar.com.br/hub/fome', true),
  (gen_random_uuid(), 'Instituto Phi', 'Fome', 'Conexão entre Doadores e Projetos', 'Rio de Janeiro', 'RJ', '', 'institutophi.org.br', '', '', '', 'https://www.paraquemdoar.com.br/hub/fome', true),
  (gen_random_uuid(), 'Instituto GAS', 'Fome', 'Combate à Pobreza Menstrual e Fome', 'São Paulo', 'SP', '', 'institutogas.org.br', '', '', '', 'https://www.paraquemdoar.com.br/hub/fome', true),
  (gen_random_uuid(), 'Redes da Maré', 'Fome', 'Desenvolvimento no Complexo da Maré', 'Rio de Janeiro', 'RJ', '', 'redesdamare.org.br', '', '', '', 'https://www.paraquemdoar.com.br/hub/fome', true),
  (gen_random_uuid(), 'Pão do Povo da Rua', 'Fome', 'Atendimento a Pessoas em Situação de Rua', 'São Paulo', 'SP', '', 'paodopovodarua.org.br', '', '', '', 'https://www.paraquemdoar.com.br/hub/fome', true),
  (gen_random_uuid(), 'Colégio Mão Amiga', 'Educação', 'Educação de Qualidade para Baixa Renda', 'São Paulo', 'SP', '', 'colegiomaoamiga.org.br', '', '', '', 'https://www.paraquemdoar.com.br/hub/fome', true),
  (gen_random_uuid(), 'Estrela da Manhã', 'Educação', 'Apoio Social e Saúde', '', 'BR', '', '', '', '', '', 'https://www.paraquemdoar.com.br/hub/domingaocomhuck', true),
  (gen_random_uuid(), 'CERVAC', 'Pessoas com Deficiência', 'Reabilitação e Inclusão Social', 'Recife', 'PE', '', 'cervac.org.br', '', '', '', 'https://www.paraquemdoar.com.br/hub/domingaocomhuck', true),
  (gen_random_uuid(), 'Mais1Code', 'Inclusão Produtiva', 'Educação Tecnológica para Jovens', 'São Paulo', 'SP', '', 'mais1code.com.br', '', '', '', 'https://www.paraquemdoar.com.br/hub/domingaocomhuck', true),
  (gen_random_uuid(), 'Balé da Ralé', 'Cultura', 'Arte e Educação em Favelas', 'Natal', 'RN', '', 'baledarale.org', '', '', '', 'https://www.paraquemdoar.com.br/hub/domingaocomhuck', true),
  (gen_random_uuid(), 'Águas Potiguara', 'Meio Ambiente', 'Preservação Ambiental e Indígena', '', 'PB', '', '', '', '', '', 'https://www.paraquemdoar.com.br/hub/domingaocomhuck', true),
  (gen_random_uuid(), 'HUMUS', 'Emergências', 'Prevenção e Resposta a Desastres', 'Belo Horizonte', 'MG', '', 'humus.org.br', '', '', '', 'https://www.paraquemdoar.com.br/hub/emergenciamg', true),
  (gen_random_uuid(), 'Movimento União BR', 'Emergências', 'Apoio a Comunidades em Catástrofes', 'São Paulo', 'SP', '', 'movimentouniaobr.com.br', '', '', '', 'https://www.paraquemdoar.com.br/hub/emergenciamg', true),
  (gen_random_uuid(), 'GRAD', 'Animais', 'Resgate de Animais em Desastres', '', 'BR', '', 'gradbrasil.org.br', '', '', '', 'https://www.paraquemdoar.com.br/hub/emergenciamg', true),
  (gen_random_uuid(), 'Todos Pela Educação', 'Educação', 'Melhoria da Educação Básica', 'São Paulo', 'SP', '', 'todospelaeducacao.org.br', '', '', '', 'https://www.paraquemdoar.com.br/busca', true),
  (gen_random_uuid(), 'ADRA', 'Emergências', 'Assistência Humanitária e Emergencial', 'Brasília', 'DF', '', 'adra.org.br', '', '', '', 'http://emergencia.paraquemdoar.com.br', true),
  (gen_random_uuid(), 'UFSC Solidária', 'Emergências', 'Apoio a Vítimas de Chuvas', 'Florianópolis', 'SC', '', 'noticias.ufsc.br', '', '76866441000132', 'BB Ag: 1453-2 CC: 203445-0', 'https://www.paraquemdoar.com.br', true);
