#!/bin/bash

echo "=== Vast.ai Instance Tunnel URLs ==="
echo

# Check if we can find the tunnel logs
if [ ! -d "/var/log" ]; then
    echo "Error: /var/log directory not found. Make sure you're running this inside the Vast.ai instance."
    exit 1
fi

# Look for tunnel URL entries
found_urls=false

grep "Default Tunnel started" /var/log/*.log 2>/dev/null | while read line; do
    if echo "$line" | grep -q "8188"; then
        url=$(echo "$line" | grep -o 'https://[^?]*')
        echo "🎨 ComfyUI: $url"
        found_urls=true
    elif echo "$line" | grep -q "1111"; then
        url=$(echo "$line" | grep -o 'https://[^?]*')
        echo "🌐 Instance Portal: $url"
        found_urls=true
    elif echo "$line" | grep -q "8080"; then
        url=$(echo "$line" | grep -o 'https://[^?]*')
        echo "📓 Jupyter: $url"
        found_urls=true
    elif echo "$line" | grep -q "8384"; then
        url=$(echo "$line" | grep -o 'https://[^?]*')
        echo "🔄 Syncthing: $url"
        found_urls=true
    fi
done

# If no URLs found, try alternative search
if ! $found_urls; then
    echo "Searching for alternative tunnel patterns..."
    
    # Look for any cloudflare URLs in logs
    urls=$(grep -r "trycloudflare.com" /var/log/ 2>/dev/null | grep -o 'https://[^[:space:]]*trycloudflare.com[^[:space:]]*' | sort -u | head -5)
    
    if [ -n "$urls" ]; then
        echo "Found these Cloudflare tunnel URLs:"
        echo "$urls" | while read url; do
            echo "🔗 $url"
        done
    else
        echo "❌ No tunnel URLs found in logs. Services may still be starting up."
        echo
        echo "💡 Tip: Wait a few minutes and run this script again."
    fi
fi

echo
echo "=== Usage Instructions ==="
echo "1. Copy the ComfyUI URL and paste it in your browser"
echo "2. If URLs don't work immediately, wait for services to fully start"
echo "3. Run this script again if you need to find the URLs later"