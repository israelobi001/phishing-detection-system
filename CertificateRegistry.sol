// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title CertificateRegistry
 * @dev Store and verify certificate hashes on the blockchain
 * @notice This contract stores certificate data immutably on Ethereum
 * @author BOUESTI Certificate Verification System
 */
contract CertificateRegistry {
    
    // Structure to hold certificate data
    struct Certificate {
        string certificateHash;  // SHA-256 hash of certificate
        string matricNumber;     // Student matric number
        uint256 timestamp;       // When it was stored on blockchain
        bool exists;             // Flag to check if certificate exists
    }
    
    // Mapping from certificate hash to Certificate struct
    // This is like a dictionary: hash => Certificate details
    mapping(string => Certificate) public certificates;
    
    // Array to keep track of all certificate hashes (for counting)
    string[] public certificateHashes;
    
    // Owner of the contract (your admin account)
    address public owner;
    
    // Events (for logging on blockchain - visible on Etherscan)
    event CertificateStored(
        string indexed certificateHash,
        string matricNumber,
        uint256 timestamp
    );
    
    // Constructor - runs once when contract is deployed
    constructor() {
        owner = msg.sender; // The account that deploys becomes owner
    }
    
    // Modifier: Only owner can call certain functions
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }
    
    /**
     * @dev Store a certificate hash on the blockchain
     * @param _certificateHash The SHA-256 hash of the certificate
     * @param _matricNumber The student's matriculation number
     * 
     * IMPORTANT: This function costs gas (ETH) to execute
     * Only the contract owner can call this function
     */
    function storeCertificate(
        string memory _certificateHash,
        string memory _matricNumber
    ) public onlyOwner {
        // Check if certificate already exists
        require(
            !certificates[_certificateHash].exists,
            "Certificate hash already exists on blockchain"
        );
        
        // Create and store the certificate
        certificates[_certificateHash] = Certificate({
            certificateHash: _certificateHash,
            matricNumber: _matricNumber,
            timestamp: block.timestamp,  // Current blockchain time
            exists: true
        });
        
        // Add to array for tracking total count
        certificateHashes.push(_certificateHash);
        
        // Emit event (viewable on Etherscan)
        emit CertificateStored(_certificateHash, _matricNumber, block.timestamp);
    }
    
    /**
     * @dev Verify if a certificate exists on the blockchain
     * @param _certificateHash The hash to verify
     * @return exists Whether the certificate exists
     * @return matricNumber The matric number associated
     * @return timestamp When it was stored
     * 
     * IMPORTANT: This is a "view" function - it's FREE to call (no gas needed)
     */
    function verifyCertificate(string memory _certificateHash)
        public
        view
        returns (
            bool exists,
            string memory matricNumber,
            uint256 timestamp
        )
    {
        Certificate memory cert = certificates[_certificateHash];
        return (cert.exists, cert.matricNumber, cert.timestamp);
    }
    
    /**
     * @dev Get the total number of certificates stored
     * @return The count of certificates
     * 
     * FREE to call (view function)
     */
    function getTotalCertificates() public view returns (uint256) {
        return certificateHashes.length;
    }
    
    /**
     * @dev Get certificate hash by index
     * @param index The index in the array
     * @return The certificate hash at that index
     * 
     * FREE to call (view function)
     */
    function getCertificateHashByIndex(uint256 index)
        public
        view
        returns (string memory)
    {
        require(index < certificateHashes.length, "Index out of bounds");
        return certificateHashes[index];
    }
    
    /**
     * @dev Transfer ownership of the contract to a new address
     * @param newOwner The address of the new owner
     * 
     * Use this if you want to change who can store certificates
     */
    function transferOwnership(address newOwner) public onlyOwner {
        require(newOwner != address(0), "New owner cannot be zero address");
        owner = newOwner;
    }
}