const express = require('express');
const bodyParser = require('body-parser');
const { Gateway, Wallets } = require('fabric-network');
const path = require('path');
const fs = require('fs');

const app = express();
app.use(bodyParser.json());

// Carpeta donde guardaste tus wallets (identidades de las orgs)
const walletPath = path.join(__dirname, 'wallet');

// Map de organizaciones y sus connection profiles
const orgs = {
  Org1: 'connection-org1.json',
  Org2: 'connection-org2.json',
  Org3: 'connection-org3.json'
};

// Función para obtener el contrato según la org
async function getContractForOrg(orgName) {
  const ccpPath = path.resolve(__dirname, 'connection-profiles', orgs[orgName]);
  const ccp = JSON.parse(fs.readFileSync(ccpPath, 'utf8'));

  const wallet = await Wallets.newFileSystemWallet(walletPath);

  const gateway = new Gateway();
  await gateway.connect(ccp, {
    wallet,
    identity: orgName.toLowerCase() + 'User', // ejemplo: org1User
    discovery: { enabled: true, asLocalhost: true }
  });

  const network = await gateway.getNetwork('mychannel');
  const contract = network.getContract('basic'); // Nombre del chaincode
  return { contract, gateway };
}

// Endpoint para crear Asset
app.post('/api/createAsset', async (req, res) => {
  const asset = req.body;
  const orgName = req.query.org; // la org seleccionada desde el front

  if (!orgName || !orgs[orgName]) return res.status(400).json({ error: 'Org inválida' });

  try {
    const { contract, gateway } = await getContractForOrg(orgName);

    // Transacción real
    await contract.submitTransaction('CreateAsset', JSON.stringify(asset));

    await gateway.disconnect();
    res.json({ status: 'Asset creado en blockchain', asset });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

app.listen(3000, () => console.log('Server corriendo en http://localhost:3000'));
