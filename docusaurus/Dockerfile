# Dockerfile for agents-docs-preview (Docusaurus)
# Node.js 20+ required for Docusaurus 3.x

FROM node:20-alpine

# Set working directory
WORKDIR /app

# Install git (required for some npm packages)
RUN apk add --no-cache git

# Copy package files first for better cache utilization
COPY package.json package-lock.json ./

# Install dependencies using npm ci for reproducible builds
RUN npm ci

# Copy the rest of the application
COPY . .

# docs directory will be symlinked to mounted volume
# The setup-symlink script or manual symlink creation is expected

# Expose Docusaurus dev server port
EXPOSE 3000

# Start development server
# --host 0.0.0.0 allows access from outside the container
CMD ["npm", "run", "start", "--", "--host", "0.0.0.0"]
