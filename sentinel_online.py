import os
# ... resto do código ...

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"✅ SERVIDOR RODANDO na porta {port}")
    server.serve_forever()