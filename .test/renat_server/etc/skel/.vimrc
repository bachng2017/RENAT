" common setting
set nocompatible
filetype off
set runtimepath^=$HOME/.vim/plugin/identLine/
set fenc=utf-8
set encoding=utf-8
scriptencoding utf-8
set number

autocmd bufreadpre *.py setlocal textwidth=80

:color desert 
syntax on

" set list
set listchars=tab:>- 

set softtabstop=4
set shiftwidth=4
set expandtab
set smarttab 

" for command mode 
nnoremap <S-Tab> <<  
" for insert mode
inoremap <S-Tab> <C-d>  

" LineIndent plugin
let g:indentLine_color_term = 111
let g:indentLine_color_gui = '#708090'
let g:indentLine_char = '|'


set wildignore=*.o,*.obj,*.pyc,*.so,*.dll
let g:python_highlight_all = 1
autocmd BufEnter *.robot :setlocal filetype=robot

