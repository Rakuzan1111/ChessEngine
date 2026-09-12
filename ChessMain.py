"""This is the main driver file. It will be responsible for handling user input and displaying the current GameState Object."""
from idlelib.config_key import MOVE_KEYS

import pygame as p


import ChessEngine
import ChessAI

from multiprocessing import Process, Queue

p.init()
BOARD_WIDTH = BOARD_HEIGHT = 512
MOVE_PANEL_WIDTH = 250
MOVE_PANEL_HEIGHT = BOARD_HEIGHT
dimension = 8
sq_size = BOARD_HEIGHT // dimension
max_fps = 15
images = {}

def loadImages():
    pieces = ['wp', 'bp', 'wR', 'wN', 'wB', 'wQ', 'wK', 'bR', 'bN', 'bB', 'bQ', 'bK']
    for piece in pieces:
        images[piece] = p.transform.scale(p.image.load('images/' + piece + '.png'), (sq_size, sq_size))

def main():
    p.init()
    screen = p.display.set_mode((BOARD_WIDTH + MOVE_PANEL_WIDTH, BOARD_HEIGHT))
    moveLogFont = p.font.SysFont('Helvitca', 18, False, False)
    clock = p.time.Clock()
    screen.fill(p.Color("white"))
    gs = ChessEngine.GameState()
    validMoves = gs.validMoves()
    moveMade = False
    animate = False
    loadImages()
    running = True
    sq_selected = ()
    player_clicks = []
    gameOver = False

    playerOne = True # If a human is playing white, then True
    playerTwo = False
    AIThinking = False
    moveFinderProcess = None
    moveUndone = False


    while running:
        humanTurn = (gs.whiteToMove and playerOne) or (not gs.whiteToMove and playerTwo)
        for e in p.event.get():
            if e.type == p.QUIT:
                running = False
            elif e.type == p.MOUSEBUTTONDOWN:
                if not gameOver:
                    location = p.mouse.get_pos()
                    col = location[0]//sq_size
                    row = location[1]//sq_size

                    if sq_selected == (row, col) or col >= 8:
                        sq_selected = ()
                        player_clicks = []
                    else:
                        sq_selected = (row, col)
                        player_clicks.append(sq_selected)

                    if len(player_clicks) == 2 and humanTurn:
                        move = ChessEngine.Move(player_clicks[0], player_clicks[1], gs.board)
                        print(move.getChessNotation())
                        for i in range(len(validMoves)):
                            if move == validMoves[i]:
                                gs.makeMove(validMoves[i])
                                moveMade = True
                                animate = True
                                sq_selected = ()
                                player_clicks = []
                        if not moveMade:
                            player_clicks = [sq_selected]

            # key handlers
            elif e.type == p.KEYDOWN:
                if e.key == p.K_z:
                    gs.undoMove()
                    sq_selected = ()
                    player_clicks = []
                    moveMade = True
                    animate = False
                    gameOver = False
                    if AIThinking:
                        moveFinderProcess.terminate()
                        AIThinking = False
                    moveUndone = True

                if e.key == p.K_r:
                    gs = ChessEngine.GameState()
                    validMoves = gs.validMoves()
                    sq_selected = ()
                    player_clicks = []
                    moveMade = False
                    animate = False
                    gameOver = False
                    moveUndone = True


        if moveMade:
            if animate:
                animateMove(gs.movelog[-1], screen, gs.board, clock)
            validMoves = gs.validMoves()
            moveMade = False
            animate = False
            moveUndone = False

            # AI move finder
        if not gameOver and not humanTurn and not moveUndone:
            if not AIThinking:
                AIThinking = True
                print("Thinking...")
                returnQueue = Queue()
                moveFinderProcess = Process(target=ChessAI.findBestMove, args=(gs, validMoves, returnQueue))
                moveFinderProcess.start()

            if not moveFinderProcess.is_alive():
                print("Done Thinking")
                AIMove = returnQueue.get()
                if AIMove is None:
                    AIMove = ChessAI.findRandomMove(validMoves)
                gs.makeMove(AIMove)
                moveMade = True
                animate = True
                AIThinking = False

        drawGameState(screen, gs, validMoves, sq_selected, moveLogFont)

        if gs.checkMate or gs.staleMate:
            gameOver = True
            if gs.staleMate:
                text = 'Stalemate'
            else:
                text = 'White wins by checkmate' if not gs.whiteToMove else 'Black wins by checkmate'
            drawEndGameText(screen, text)
        clock.tick(max_fps)
        p.display.flip()

def drawGameState(screen, gs, validMoves, sqSelected, moveLogFont):
    drawBoard(screen)
    highlightSquares(screen, gs, validMoves, sqSelected)
    drawPieces(screen, gs.board)
    drawMoveLog(screen, gs, moveLogFont)

def drawBoard(screen):
    global colors
    colors = [p.Color('white'), p.Color('dark green')]
    for r in range(dimension):
        for c in range(dimension):
            color = colors[((r+c) % 2)]
            p.draw.rect(screen, color, p.Rect(c*sq_size, r*sq_size, sq_size, sq_size))

def highlightSquares(screen, gs, validMoves, sqSelected):
    if sqSelected != ():
        r, c = sqSelected
        if gs.board[r][c][0] == ('w' if gs.whiteToMove else 'b'):
            s = p.Surface((sq_size, sq_size))
            s.set_alpha(100)
            s.fill(p.Color('blue'))
            screen.blit(s, (c*sq_size, r*sq_size))
            s.fill(p.Color('yellow'))
            for move in validMoves:
                if move.startRow == r and move.startCol == c:
                    screen.blit(s, (move.endCol*sq_size, sq_size*move.endRow))
    if gs.inCheckStatus:
        s = p.Surface((sq_size, sq_size))
        s.set_alpha(100)
        s.fill(p.Color("red"))

        if gs.whiteToMove:
            screen.blit(s, (gs.whiteKingLocation[1] * sq_size,
                            gs.whiteKingLocation[0] * sq_size))
        else:
            screen.blit(s, (gs.blackKingLocation[1] * sq_size,
                            gs.blackKingLocation[0] * sq_size))

def drawPieces(screen, board):
    for r in range(dimension):
        for c in range(dimension):
            piece = board[r][c]
            if piece != '--':
                screen.blit(images[piece], p.Rect(c*sq_size, r*sq_size, sq_size, sq_size))

def drawMoveLog(screen, gs, font):

    moveLogRect = p.Rect(BOARD_WIDTH, 0, MOVE_PANEL_WIDTH, MOVE_PANEL_HEIGHT)
    p.draw.rect(screen, p.Color('black'), moveLogRect)
    moveLog = gs.movelog
    moveTexts = []
    for i in range(0, len(moveLog), 2):
        moveString = str(i//2 + 1) + ". " + str(moveLog[i]) + " "
        if i + 1 < len(moveLog):
            moveString += str(moveLog[i+1])
        moveTexts.append(moveString)

    movesPerRow = 3
    padding = textY = 5
    for i in range(0, len(moveTexts), movesPerRow):
        text = ""
        for j in range(movesPerRow):
            if i + j < len(moveTexts):
                text += moveTexts[i+j] + '    '
        textObject = font.render(text, True, p.Color('white'))
        textLocation = moveLogRect.move(padding, textY)
        screen.blit(textObject, textLocation)
        textY += textObject.get_height()


def drawEndGameText(screen, text):
    font = p.font.SysFont('Helvitca', 32, True, False )
    textObject = font.render(text, 0, p.Color('Grey'))
    textLocation = p.Rect(0, 0, BOARD_WIDTH, BOARD_HEIGHT).move(BOARD_WIDTH / 2 - textObject.get_width() / 2, BOARD_HEIGHT / 2 - textObject.get_height() / 2)
    screen.blit(textObject, textLocation)
    textObject = font.render(text, 0, p.Color('Red'))
    screen.blit(textObject, textLocation.move(2, 2))

def animateMove(move, screen, board, clock):
    global colors
    coords = []
    dR = move.endRow - move.startRow
    dC = move.endCol - move.startCol
    framePerSquare = 8
    frameCount = (abs(dR) + abs(dC)) * framePerSquare
    for frame in range(frameCount + 1):
        r, c = ((move.startRow + dR*frame/frameCount, move.startCol + dC*frame/frameCount))
        drawBoard(screen)
        drawPieces(screen, board)
        #erase piece moved from ending square
        color = colors[(move.endRow + move.endCol) % 2]
        endSquare = p.Rect(move.endCol*sq_size, move.endRow*sq_size, sq_size, sq_size)
        p.draw.rect(screen, color, endSquare)
        #draw captured piece onto rectangle
        if move.pieceCaptured != '--':
            if move.isEnpassantMove:
                enPassantRow = move.endRow + 1 if move.pieceCaptured[0] == 'b' else move.endRow - 1
                endSquare = p.Rect(move.endCol * sq_size, enPassantRow * sq_size, sq_size, sq_size)
            screen.blit(images[move.pieceCaptured], endSquare)
        screen.blit(images[move.pieceMoved], p.Rect(c*sq_size, r*sq_size, sq_size, sq_size))
        p.display.flip()
        clock.tick(300)

if __name__ == '__main__':
    main()



