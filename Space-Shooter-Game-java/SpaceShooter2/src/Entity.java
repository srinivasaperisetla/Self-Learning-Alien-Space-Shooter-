import java.awt.*;
import javax.swing.*;
import java.util.*;
import java.awt.event.*;

public class Entity extends JComponent{
	
	Image image;
	int x;
	int y;
	int xVelocity;
	int yVelocity;
	
	public Entity(Image icon, int xpos, int ypos) {
		image = icon; 
		x = xpos;
		y = ypos;
	}
		
	 
	public void setXDirection(int xDirection) {
		xVelocity = xDirection;
	}
	
	public void setYDirection(int yDirection) {
		yVelocity = yDirection;
	}
	
	public void move() {
		x = x + xVelocity;
		y = y + yVelocity;
	}
	
	public void paintComponent(Graphics g) {
		super.paintComponent(g);
		g.drawImage(image,x,y,null);
		
	}

}
