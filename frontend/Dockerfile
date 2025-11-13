FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run dev server
CMD ["npm", "run", "dev"]
