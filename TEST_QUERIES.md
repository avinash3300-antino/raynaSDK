# Test Queries for Rayna Tours ChatGPT App

## Show Tours (show-tours)

### Basic city search
- "Show me tours in Dubai"
- "What activities are available in Bangkok?"
- "Find tours in Singapore"
- "Show me things to do in Bali"

### Category filtering
- "Show me desert safari experiences in Dubai"
- "Find cruise options in Dubai"
- "What theme parks are in Abu Dhabi?"
- "Show cultural tours in Bangkok"

### Price filtering
- "Tours in Dubai under 200 AED"
- "Budget tours in Bangkok under 150 AED"
- "Show me affordable activities in Singapore under 100 AED"

### Combined filters
- "Adventure tours in Dubai under 200 AED"
- "Cultural tours in Bangkok, limit to 4"

## Tour Details (show-tour-detail)

### By name
- "Tell me more about Dubai Desert Safari"
- "Show details for Burj Khalifa At The Top"
- "What's included in the Phi Phi Island Day Trip?"

### By URL
- "Show details for https://www.raynatours.com/dubai/adventure/desert-safari-e-509001"

## Compare Tours (compare-tours)

- "Compare Dubai Desert Safari and Burj Khalifa At The Top"
- "Compare Phi Phi Island, Phuket Sunset Cruise, and Krabi Four Islands"
- "How does Ferrari World compare to Atlantis Aquaventure?"

## Holiday Packages (show-holiday-packages)

- "Show holiday packages in Dubai"
- "Any holiday deals in Abu Dhabi?"

## Visa Info (get-visa-info)

- "Do I need a visa for the USA?"
- "Visa information for UK"
- "What visas are available for Australia?"

## Fallback / Edge Cases

- "Tours in Dammam" (may trigger static DB fallback)
- "Show me tours in Makkah" (limited availability, tests fallback)
- "Compare Mount Batur and Ubud Rice Terraces" (Bali tours)
