<p align="center">
  <img src="../assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

# Turno de conversa

O turno começa com uma mensagem autenticada e termina com uma resposta e a classificação do resultado. A conversa entre agentes se relaciona ao [fluxo central](https://github.com/Solierrr/docs-warehouse/blob/main/docs/flows/ASSISTANT_CHAT.md).

```mermaid
flowchart TD
 A[Mensagem e JWT] --> B{Token aceito?}
 B -->|não| E[Erro HTTP]
 B -->|sim| G[Guardrail de entrada]
 G --> R[Roteamento e especialistas]
 R --> O[Orquestração e revisão]
 O --> S[Guardrail de saída]
 S --> F[Resposta e outcome]
```

Um token inválido produz 401 e um corpo inválido produz 422, enquanto as falhas de ferramentas e a troca de modelo por alternativa ficam registradas no resultado do turno. O Mongo mantém os checkpoints da conversa, e o histórico é enviado ao serviço de mensagens.