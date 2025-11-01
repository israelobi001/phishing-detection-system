"""
Blockchain Integration Module for BOUESTI Certificate Verification System
Handles Web3 connection and smart contract interactions
"""

from web3 import Web3
from eth_account import Account
import json
import os

class BlockchainManager:
    """
    Manages blockchain interactions for certificate storage and verification
    """
    
    def __init__(self, infura_url, contract_address, contract_abi, private_key):
        """
        Initialize blockchain connection
        
        Args:
            infura_url: Your Infura project URL (e.g., https://sepolia.infura.io/v3/YOUR_KEY)
            contract_address: Deployed contract address (e.g., 0x123...)
            contract_abi: Contract ABI (JSON format)
            private_key: Your wallet private key (keep secret!)
        """
        self.w3 = Web3(Web3.HTTPProvider(infura_url))
        self.contract_address = contract_address
        self.private_key = private_key
        
        # Get account from private key
        self.account = Account.from_key(private_key)
        self.account_address = self.account.address
        
        # Initialize contract
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=contract_abi
        )
        
        print(f"✅ Connected to blockchain")
        print(f"✅ Account: {self.account_address}")
        print(f"✅ Contract: {contract_address}")
    
    def is_connected(self):
        """Check if Web3 is connected to the network"""
        return self.w3.is_connected()
    
    def get_balance(self):
        """Get account balance in ETH"""
        balance_wei = self.w3.eth.get_balance(self.account_address)
        balance_eth = self.w3.from_wei(balance_wei, 'ether')
        return float(balance_eth)
    
    def store_certificate_on_blockchain(self, certificate_hash, matric_number):
        """
        Store certificate hash on blockchain
        
        Args:
            certificate_hash: SHA-256 hash of certificate
            matric_number: Student matric number
            
        Returns:
            dict: Transaction details or error
        """
        try:
            # Check connection
            if not self.is_connected():
                return {
                    'success': False,
                    'error': 'Not connected to blockchain network'
                }
            
            # Check balance
            balance = self.get_balance()
            if balance < 0.001:  # Minimum balance check
                return {
                    'success': False,
                    'error': f'Insufficient balance: {balance} ETH. Need at least 0.001 ETH'
                }
            
            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.account_address)
            
            # Estimate gas
            gas_estimate = self.contract.functions.storeCertificate(
                certificate_hash,
                matric_number
            ).estimate_gas({'from': self.account_address})
            
            # Build transaction
            transaction = self.contract.functions.storeCertificate(
                certificate_hash,
                matric_number
            ).build_transaction({
                'from': self.account_address,
                'nonce': nonce,
                'gas': gas_estimate + 10000,  # Add buffer
                'gasPrice': self.w3.eth.gas_price,
            })
            
            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(
                transaction,
                private_key=self.private_key
            )
            
            # Send transaction (Web3.py v6+ compatibility)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            print(f"📤 Transaction sent: {tx_hash.hex()}")
            print(f"⏳ Waiting for confirmation...")
            
            # Wait for transaction receipt (confirmation)
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if tx_receipt['status'] == 1:
                print(f"✅ Transaction confirmed in block {tx_receipt['blockNumber']}")
                return {
                    'success': True,
                    'tx_hash': tx_hash.hex(),
                    'block_number': tx_receipt['blockNumber'],
                    'gas_used': tx_receipt['gasUsed']
                }
            else:
                return {
                    'success': False,
                    'error': 'Transaction failed on blockchain',
                    'tx_hash': tx_hash.hex()
                }
                
        except Exception as e:
            print(f"❌ Blockchain error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_certificate_on_blockchain(self, certificate_hash):
        """
        Verify if certificate exists on blockchain
        
        Args:
            certificate_hash: SHA-256 hash to verify
            
        Returns:
            dict: Verification result
        """
        try:
            # Call smart contract view function (no gas needed)
            result = self.contract.functions.verifyCertificate(
                certificate_hash
            ).call()
            
            exists, matric_number, timestamp = result
            
            if exists:
                # Convert timestamp to readable format
                from datetime import datetime
                date_stored = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                
                return {
                    'exists': True,
                    'matric_number': matric_number,
                    'timestamp': timestamp,
                    'date_stored': date_stored
                }
            else:
                return {
                    'exists': False
                }
                
        except Exception as e:
            print(f"❌ Verification error: {str(e)}")
            return {
                'exists': False,
                'error': str(e)
            }
    
    def get_total_certificates(self):
        """Get total number of certificates stored on blockchain"""
        try:
            total = self.contract.functions.getTotalCertificates().call()
            return total
        except Exception as e:
            print(f"❌ Error getting total: {str(e)}")
            return 0


# Contract ABI - This will be generated when you deploy the contract
# For now, this is a placeholder. You'll replace this after deployment.
CONTRACT_ABI = [
    {
        "inputs": [],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "string",
                "name": "certificateHash",
                "type": "string"
            },
            {
                "indexed": False,
                "internalType": "string",
                "name": "matricNumber",
                "type": "string"
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "timestamp",
                "type": "uint256"
            }
        ],
        "name": "CertificateStored",
        "type": "event"
    },
    {
        "inputs": [
            {
                "internalType": "string",
                "name": "",
                "type": "string"
            }
        ],
        "name": "certificates",
        "outputs": [
            {
                "internalType": "string",
                "name": "certificateHash",
                "type": "string"
            },
            {
                "internalType": "string",
                "name": "matricNumber",
                "type": "string"
            },
            {
                "internalType": "uint256",
                "name": "timestamp",
                "type": "uint256"
            },
            {
                "internalType": "bool",
                "name": "exists",
                "type": "bool"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "index",
                "type": "uint256"
            }
        ],
        "name": "getCertificateHashByIndex",
        "outputs": [
            {
                "internalType": "string",
                "name": "",
                "type": "string"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getTotalCertificates",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [
            {
                "internalType": "address",
                "name": "",
                "type": "address"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "string",
                "name": "_certificateHash",
                "type": "string"
            },
            {
                "internalType": "string",
                "name": "_matricNumber",
                "type": "string"
            }
        ],
        "name": "storeCertificate",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "string",
                "name": "_certificateHash",
                "type": "string"
            }
        ],
        "name": "verifyCertificate",
        "outputs": [
            {
                "internalType": "bool",
                "name": "exists",
                "type": "bool"
            },
            {
                "internalType": "string",
                "name": "matricNumber",
                "type": "string"
            },
            {
                "internalType": "uint256",
                "name": "timestamp",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]


def initialize_blockchain():
    """
    Initialize blockchain connection with environment variables
    
    Required environment variables:
    - INFURA_URL: Your Infura project URL
    - CONTRACT_ADDRESS: Deployed contract address
    - PRIVATE_KEY: Your wallet private key
    """
    
    # Get configuration from environment variables
    infura_url = os.getenv('INFURA_URL')
    contract_address = os.getenv('CONTRACT_ADDRESS')
    private_key = os.getenv('PRIVATE_KEY')
    
    if not all([infura_url, contract_address, private_key]):
        print("⚠️ Blockchain not configured. Set environment variables:")
        print("   - INFURA_URL")
        print("   - CONTRACT_ADDRESS")
        print("   - PRIVATE_KEY")
        return None
    
    try:
        blockchain = BlockchainManager(
            infura_url=infura_url,
            contract_address=contract_address,
            contract_abi=CONTRACT_ABI,
            private_key=private_key
        )
        return blockchain
    except Exception as e:
        print(f"❌ Failed to initialize blockchain: {str(e)}")
        return None