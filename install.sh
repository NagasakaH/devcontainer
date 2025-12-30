#!/bin/bash

# move to script dir
cd "$(dirname "$0")"

# install devcontainer cli
if ! devcontainer -v; then
	sudo npm install -g @devcontainers/cli
fi

# install .tmux.conf
if [ -e "$HOME/.tmux.conf" ]; then
	mv $HOME/.tmux.conf $HOME/.tmux.conf.old
fi
ln -s $PWD/dotfiles/.tmux.conf $HOME/.tmux.conf

# install lazyvim

# install devcontainer command
