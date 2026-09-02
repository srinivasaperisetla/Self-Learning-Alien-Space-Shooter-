import java.awt.*;
import java.awt.event.MouseAdapter;
import javax.swing.*;
import java.util.*;
import java.awt.event.*;

public class GamePanel extends JPanel implements Runnable{
	
	static final int GAME_WIDTH = 500;
	static final int GAME_HEIGHT = 500;
	static final Dimension SCREEN_SIZE = new Dimension(GAME_WIDTH,GAME_HEIGHT);
	Thread gameThread;
	Image image;
	Graphics graphics;
	Label score;
	Label lives;
	Label title;
	Label credentials;
	Label start;
	Label gameover;
	Entity player;
	Entity enemy1;
	Entity enemy2;
	Entity enemy3;
	Entity redLaser;
	Entity blueLaser;
	Entity heart;
	boolean running = false;
	boolean end = false;
	
	public GamePanel() {
		
		setFocusable(true);
		addKeyListener(new AL());
		setPreferredSize(SCREEN_SIZE);
		
		newEntities();
		
		gameThread = new Thread(this);
		gameThread.start();
		

		
	}
	
	public void newEntities() {
		ImageIcon i = new ImageIcon("spaceship.png");
		ImageIcon ie1 = new ImageIcon("enemy1.png");
		ImageIcon ie2 = new ImageIcon("enemy2.png");
		ImageIcon ie3 = new ImageIcon("enemy3.png");
		ImageIcon i1 = new ImageIcon("laser.png");
		ImageIcon i2 = new ImageIcon("bluelaser.png");
		ImageIcon h = new ImageIcon("heart.png");
		
		player = new Entity(i.getImage(),200,415);
		
		redLaser = new Entity(i1.getImage(),600,-100);

		
		enemy1 = new Entity(ie1.getImage(),(int)(Math.random()*415),-1*(int)((Math.random()*500)+100)); //normal enemy
		enemy2 = new Entity(ie2.getImage(),(int)(Math.random()*417),-1*(int)((Math.random()*5000)+1000));//fast
		enemy3 = new Entity(ie3.getImage(),(int)(Math.random()*405),-1*(int)((Math.random()*700)+300));//laser
		
		blueLaser = new Entity(i2.getImage(),600,-100);
		
		heart = new Entity(h.getImage(),(int)(Math.random()*471),2000);
		//heart = new Entity(h.getImage(),(int)(Math.random()*471),100);
		score = new Label("",20,425,25,true);
		lives = new Label("Lives: ",15,425,45, true);
		lives.score = 3;
		title = new Label("SpaceShooter",60,60,175,false);
		credentials = new Label("Created By: Srini, Cyrus, Ryan and D2 Mo",15, 100,225,false);
		start = new Label("Press Enter or Space",30, 95,275,false);
		gameover = new Label("Game Over!", 60, 95, 225, false);
		

		
	}
	
	public void paint(Graphics g) {
		image = createImage(getWidth(),getHeight());
		graphics = image.getGraphics();
		draw(graphics);
		g.drawImage(image,0,0,this);
		
	}
	
	public void draw(Graphics g) {
		redLaser.paintComponent(g);
		blueLaser.paintComponent(g);
		heart.paintComponent(g);
		player.paintComponent(g);
		enemy1.paintComponent(g);
		enemy2.paintComponent(g);
		enemy3.paintComponent(g);
		score.draw(g);
		lives.draw(g);
		if(!running) {
			title.draw(g);
			credentials.draw(g);
			start.draw(g);
		}
		if(end) {
			gameover.draw(g);
		}
	}
	
	public void move() {
		player.move();
		redLaser.move();
		blueLaser.move();
		enemy1.move();
		enemy2.move();
		enemy3.move();
		heart.move();
	}
	
	public void checkCollision() {
		if(player.x<=0) {
			player.x=0;
		}
		if(player.x>=400) {
			player.x = 400;
		}
		if(blueLaser.y>=1000 && enemy3.y>-90) {
			blueLaser.x = enemy3.x+39;
			blueLaser.y = enemy3.y+20;
		}
		if(enemy1.y>500) {
			enemy1.x = (int)(Math.random()*415);
			enemy1.y = -1*(int)((Math.random()*400)+100);
			lives.score--;
			
		}
		if(enemy2.y>500) {
			enemy2.x = (int)(Math.random()*417);
			enemy2.y = -1*(int)((Math.random()*4000)+1000);
			lives.score--;
			
		}
		if(enemy3.y>500) {
			enemy3.x = (int)(Math.random()*405);
			enemy3.y =-1*(int)((Math.random()*700)+300);
			lives.score--;
		}
		
		if(heart.y>700) {
			heart.x = (int)(Math.random()*471);
			heart.y = -1*(int)((Math.random()*7500)+3500);		
		}
		
		
		
		if(redLaser.x >= enemy1.x-15 && redLaser.x <= enemy1.x+86 && redLaser.y<=enemy1.y+75 && redLaser.y>=enemy1.y) {
			redLaser.y = -100;
			redLaser.x = 600;
			enemy1.x = (int)(Math.random()*415);
			enemy1.y = -1*(int)((Math.random()*400)+100);
			score.score = score.score +10;
			
		}
		
		if(redLaser.x >= enemy2.x-15 && redLaser.x <= enemy2.x+84 && redLaser.y<=enemy2.y+75 && redLaser.y>=enemy2.y) {
			redLaser.y = -100;
			redLaser.x = 600;
			enemy2.x = (int)(Math.random()*417);
			enemy2.y = -1*(int)((Math.random()*5000)+1000);
			score.score = score.score +10;			
		}
		
		if(redLaser.x >= enemy3.x-15 && redLaser.x <= enemy3.x+96 && redLaser.y<=enemy3.y+75 && redLaser.y>=enemy3.y) {
			redLaser.y = -100;
			redLaser.x = 600;
			enemy3.x = (int)(Math.random()*405);
			enemy3.y = -1*(int)((Math.random()*700)+300);
			score.score = score.score +10;			
		}
 		
		if (enemy1.x>=player.x-75&& enemy1.x<=player.x+75 && enemy1.y>=335) {
			enemy1.x = (int)(Math.random()*415);
			enemy1.y = -1*(int)((Math.random()*400)+100);
			lives.score--;
		}
		
		if (enemy2.x>=player.x-75&& enemy2.x<=player.x+75 && enemy2.y>=335) {
			enemy2.x = (int)(Math.random()*417);
			enemy2.y = -1*(int)((Math.random()*5000)+1000);
			lives.score--;
		}
		
		if (enemy3.x>=player.x-90&& enemy3.x<=player.x+90 && enemy3.y>=335) {
			enemy3.x = (int)(Math.random()*405);
			enemy3.y = -1*(int)((Math.random()*700)+300);
			lives.score--;
		}
		if (blueLaser.x>=player.x-15&& blueLaser.x<=player.x+82 && blueLaser.y>=415 && blueLaser.y<=430) {
			blueLaser.x = enemy3.x+39;
			blueLaser.y = enemy3.y+20;
					
			lives.score--;
		}
		
		if(heart.x>=player.x-25 && heart.x<=player.x+80 && heart.y >= 405) {
			lives.score++;
			heart.x = (int)(Math.random()*471);
			heart.y = -1*(int)((Math.random()*1000)+2000);		
		}
		
		if(lives.score <=0) {
			end = true;
			enemy1.setYDirection(0);
			enemy2.setYDirection(0);
			enemy3.setYDirection(0);
			blueLaser.setYDirection(0);
			redLaser.setYDirection(0);
			heart.setYDirection(0);
		}
		
	}
	
	public void run() {
		//game loop
		long lastTime = System.nanoTime();
		double amountOfTicks = 60.0;
		double ns = 1000000000 / amountOfTicks;
		double delta = 0;
		while(true) {
			long now = System.nanoTime();
			delta +=(now - lastTime)/ns;
			lastTime = now;
			if(delta >= 1) {
				move();
				checkCollision();
				repaint();
				delta--;
				
			}
			
		}
		
	}
	
	public class AL extends KeyAdapter {
		
		public void keyPressed(KeyEvent e) {
			switch(e.getKeyCode()) {
			case KeyEvent.VK_LEFT:
					player.setXDirection(-10);
					player.move();
					break;
			case KeyEvent.VK_RIGHT:	
					player.setXDirection(10);
					player.move();
					break;
			case KeyEvent.VK_SPACE:
				if(redLaser.y<=30) {
				redLaser.y = 400;
				redLaser.x = player.x+32;
				}
			case KeyEvent.VK_ENTER:
				if(!running) {
					running = true;
					enemy1.setYDirection(3);
					enemy2.setYDirection(7);
					enemy3.setYDirection(1);
					blueLaser.setYDirection(12);
					redLaser.setYDirection(-12);
					heart.setYDirection(2);
					
				}
			}	
		}
		
		public void keyReleased(KeyEvent e) {
			switch(e.getKeyCode()) {
			case KeyEvent.VK_LEFT:
					player.setXDirection(0);
					player.move();
					break; 
			case KeyEvent.VK_RIGHT:	
					player.setXDirection(0);
					player.move();
					break;
			case KeyEvent.VK_SPACE:
				redLaser.y = redLaser.y;
				redLaser.x = redLaser.x;
			}
			
		}
	}

}
