const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');

const app = express();
const PORT = 3000;

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(express.static('frontend')); // tu index.html debe estar en carpeta "public"

// Lista de organizaciones simulada
const organizations = [
  { id: 'org1', name: 'Org1' },
  { id: 'org2', name: 'Org2' },
  { id: 'org3', name: 'Org3' }
];

// Endpoint para obtener organizaciones
app.get('/api/organizations', (req, res) => {
  res.json(organizations);
});

// Endpoint para "conectar" a la organización
app.post('/api/connect', (req, res) => {
  const { orgId } = req.body;
  const org = organizations.find(o => o.id === orgId);

  if (!org) {
    return res.status(400).json({ error: 'Organización no válida' });
  }

  // Aquí iría la lógica real para inicializar la conexión con Hyperledger
  console.log(`Conectando a ${org.name}...`);

  res.json({ orgName: org.name, status: 'connected' });
});

// Arrancar servidor
app.listen(PORT, () => {
  console.log(`Servidor corriendo en http://localhost:${PORT}`);
});
